import os
import sys
import time

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser
from reader import CODE
import re

# LangChain のテキスト分割器と LLM（ChatOpenAI）を利用するためのインポート
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

lang_obj = tsjava.language()
JAVA_LANGUAGE = Language(lang_obj)

parser = Parser(JAVA_LANGUAGE)

# コード読み込み
code = CODE

def main():
	# パースを実行して method_declaration を収集する
	try:
		codedata = bytes(code, 'utf8')
		tree = parser.parse(codedata)
	except Exception as e:
		print(f"パース時に例外が発生しました: {e}")
		raise

	root_node = tree.root_node

	chunks = []

	def get_node_name(node):
		for c in node.children:
			if c.type == 'identifier':
				return c.text.decode('utf8')
		return None

	def collect_chunks(node, parent_name=None):
		"""指定ノード以下を再帰的に探索し、メソッド宣言を chunks に追加する。"""
		if node.type == 'class_declaration':
			parent_name = get_node_name(node)
		if node.type == 'method_declaration':
			chunks.append({
				'code': node.text.decode('utf8'),
				'parent': parent_name,
				'name': get_node_name(node),
				'type': node.type,
				'start_line': node.start_point[0],
				'end_line': node.end_point[0]
			})
			print(f"収集したチャンク: {node.type} (行 {node.start_point[0]+1} から {node.end_point[0]+1} まで)")
		for c in node.children:
			collect_chunks(c, parent_name)
	
	collect_chunks(root_node)

	# 取得したチャンクのcodeをRecursiveTextSplitterを利用して分割する
	# 分割した各チャンクのコードを LangChain の
	# RecursiveCharacterTextSplitter を使って分割し、
	# 各分割に対して LLM（OpenAI）で日本語の解説文を作成して
	# 各 dict 要素に 'explanation' を追加する。
	#
	# 注意:
	# - セパレータは "改行が2連続" のみとする。ただしその間に空白/タブが
	#   含まれる場合も同様とみなすため、事前に正規化を行う。
	# - 分割後の各要素は以下のキーを持つ dict とする:
	#   { 'parent':..., 'name':..., 'piece_code':..., 'start_line':..., 'end_line':..., 'explanation':... }
	
	# LangChain の利用可否チェック
	# テキストスプリッタの初期化（分割条件は "\n\n" のみ）
	# separator は厳密一致で扱われるため、事前に正規化してから分割する
	splitter = RecursiveCharacterTextSplitter(separators=["\n\n"], chunk_size=2000, chunk_overlap=0)

	# 分割結果を格納するリスト
	split_chunks = []

	for ch in chunks:
		orig_code = ch['code']
		# CRLF を LF に正規化
		normal_code = orig_code.replace('\r\n', '\n').replace('\r', '\n')
		# 空白/タブを含む二重改行を通常の "\n\n" に正規化
		normal_code = re.sub(r"\n[ \t]+\n", "\n\n", normal_code)

		# 実際に分割する
		pieces = splitter.split_text(normal_code)

		for piece in pieces:
			# 元の行番号を近似計算する。
			# piece が orig_code に現れる最初の位置を検索して、その前の改行数から開始行を求める
			offset = orig_code.find(piece)
			if offset == -1:
				# 正規化の違いなどで見つからない場合は start_line を元チャンクの start を使う
				piece_start = ch['start_line']
			else:
				line_offset = orig_code[:offset].count('\n')
				piece_start = ch['start_line'] + line_offset
			piece_end = piece_start + piece.count('\n')

			entry = {
				'parent': ch.get('parent'),
				'name': ch.get('name'),
				'piece_code': piece,
				'start_line': piece_start,
				'end_line': piece_end,
				'explanation': None,
			}
			split_chunks.append(entry)

	# LLM を使って各分割片の解説を取得する
	try:
		# ChatOpenAI を使用してチャット形式でプロンプトを送信する
		llm = ChatOpenAI(temperature=0)
	except Exception as e:
		print(f"ChatOpenAI クライアントの初期化に失敗しました: {e}\nフォールバック動作を行います。")
		llm = None

	for idx, entry in enumerate(split_chunks):
		code_snippet = entry['piece_code']
		prompt = ("以下の Java コードについて、日本語で分かりやすく解説してください。"\
			"メソッドの目的、重要な処理、注意点（例外/前提）を含めてください。コードをそのまま繰り返す必要はありません。\n\n" + code_snippet)
		try:
			# ChatOpenAI はチャットメッセージを受け取る
			response = llm.invoke([HumanMessage(content=prompt)])
			# 戻り値の形式はバージョンにより異なるため柔軟に扱う
			if isinstance(response, str):
				explanation = response
			else:
				# AIMessage の場合は .content
				if hasattr(response, 'content'):
					explanation = response.content
				else:
					# リストや生成オブジェクトの場合のフォールバック
					try:
						# 例: [AIMessage(...)] のような場合
						if isinstance(response, list) and len(response) > 0 and hasattr(response[0], 'content'):
							explanation = response[0].content
						else:
							explanation = str(response)
					except Exception:
						explanation = str(response)
		except Exception as e:
			print(f"LLM 呼び出しでエラー: {e}")
			explanation = f"LLM 呼び出しでエラーが発生しました: {e}"
		entry['explanation'] = explanation
	# 動作確認用の簡易出力
	print(f"分割済みチャンク数: {len(split_chunks)}")
	if len(split_chunks) > 0:
		# 先頭3件をサンプル表示
		for s in split_chunks[:3]:
			print('---')
			print(f"parent: {s['parent']}, name: {s['name']}, lines: {s['start_line']+1}-{s['end_line']+1}")
			print(f"explanation (先頭100文字): { (s['explanation'] or '')[:100] }")

	# ファイルに保存する例
	output_file = 'chunked_explanations.txt'
	with open(output_file, 'w', encoding='utf-8') as f:
		for s in split_chunks:
			f.write('---\n')
			f.write(f"parent: {s['parent']}, name: {s['name']}, lines: {s['start_line']+1}-{s['end_line']+1}\n")
			f.write(f"explanation:\n{s['explanation']}\n")

if __name__ == '__main__':
	main()

