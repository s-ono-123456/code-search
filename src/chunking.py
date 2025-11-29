import os
import sys
import time

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser
from reader import CODE

lang_obj = tsjava.language()
JAVA_LANGUAGE = Language(lang_obj)

parser = Parser(JAVA_LANGUAGE)

# テスト用のコード（元々のファイルにあったサンプルコード）

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

	def collect_chunks(node, parent_name=None):
		"""指定ノード以下を再帰的に探索し、メソッド宣言を chunks に追加する。"""
		if node.type == 'class_declaration':
			parent_name = get_node_name(node)
		if node.type == 'method_declaration':
			try:
				chunk_code = codedata[node.start_byte:node.end_byte].decode('utf8')
			except Exception:
				chunk_code = ''
			chunks.append({
				'code': chunk_code,
				'text': node.text.decode('utf8'),
				'parent': parent_name,
				'name': get_node_name(node),
				'type': node.type,
				'start_line': node.start_point[0],
				'end_line': node.end_point[0]
			})
			print(f"収集したチャンク: {node.type} (行 {node.start_point[0]+1} から {node.end_point[0]+1} まで)")
		for c in node.children:
			collect_chunks(c, parent_name)
	
	def get_node_name(node):
		for c in node.children:
			if c.type == 'identifier':
				return c.text.decode('utf8')
		return None

	collect_chunks(root_node)

	created_files = []
	for i, chunk in enumerate(chunks):
		filename = f'chunk_{i+1}_{chunk["type"]}_lines_{chunk["start_line"]+1}_to_{chunk["end_line"]+1}.java'
		with open(filename, 'w', encoding='utf8') as f:
			f.write(chunk['code'])
		created_files.append(filename)

	# 最後に簡潔なサマリを出力
	print(f"処理完了: {len(created_files)} 個のチャンクを保存し、それぞれに説明ファイルを生成しました。")


if __name__ == '__main__':
	main()

