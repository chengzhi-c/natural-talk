# -*- coding: utf-8 -*-
"""AC自动机（Aho-Corasick）极简实现 — 单遍扫描多模式匹配.

零依赖，仅标准库。用于 T1/T2/T4/T5 词表的高效命中。
复杂度: 构建 O(total_chars), 扫描 O(n)
"""
from collections import deque

class ACTrie:
    def __init__(self):
        self.next = [{}]      # 状态转移
        self.fail = [0]       # 失败指针
        self.out = [[]]       # 输出：[(word, tier)]

    def add(self, word, tier, label=None):
        node = 0
        for ch in word.lower():
            nxt = self.next[node].get(ch)
            if nxt is None:
                self.next[node][ch] = len(self.next)
                self.next.append({})
                self.fail.append(0)
                self.out.append([])
                nxt = len(self.next) - 1
            node = nxt
        self.out[node].append((word, tier, label or word))

    def build(self):
        q = deque()
        for ch, nxt in self.next[0].items():
            self.fail[nxt] = 0
            q.append(nxt)
        while q:
            r = q.popleft()
            for ch, nxt in self.next[r].items():
                q.append(nxt)
                f = self.fail[r]
                while f and ch not in self.next[f]:
                    f = self.fail[f]
                self.fail[nxt] = self.next[f].get(ch, 0)
                self.out[nxt].extend(self.out[self.fail[nxt]])

    def scan(self, text):
        node = 0
        low = text.lower()
        for i, ch in enumerate(low):
            while node and ch not in self.next[node]:
                node = self.fail[node]
            node = self.next[node].get(ch, 0)
            for word, tier, label in self.out[node]:
                yield (i - len(word) + 1, word, tier, label)

def build_default_trie():
    import json
    from pathlib import Path
    lex_path = Path(__file__).resolve().parent.parent / "dist" / "lexicon.json"
    if lex_path.exists():
        lex = json.loads(lex_path.read_text(encoding="utf-8"))
    else:
        lex = {}
    trie = ACTrie()
    for w in lex.get("tier1_identity", []):
        trie.add(w, "T1")
    for w in lex.get("tier1_courtesy", []):
        trie.add(w, "T1")
    for w in lex.get("tier2", []):
        trie.add(w, "T2")
    for w in lex.get("signposts", []):
        trie.add(w, "SIGNPOST")
    # Tier4/T5 可按需追加（当前由正则与密度层覆盖，保持Trie轻量）
    trie.build()
    return trie
