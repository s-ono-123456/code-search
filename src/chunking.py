import os
import sys
import time

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser
from reader import CODE

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
	
	# 分割した各チャンクのコードをLangchainに渡し、LLMで解説文を作成する


if __name__ == '__main__':
	main()

