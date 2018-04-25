#!/usr/local/bin/python2.7

from __future__ import division
import argparse
from collections import defaultdict
import json
from math import log
import os

def replace_rare(filename, outputname):
    word_count = defaultdict(int)
    def word_count_node(node):
        for n in node[1:]:
            if type(n) is list:
                word_count_node(n)
            else:
                word_count[n] += 1

    parse_data = []
    with open(filename) as f:
        for line in f:
            parsed = json.loads(line.strip()) 
            parse_data.append(parsed)
            word_count_node( parsed )
    rare_words = set(w for w,c in word_count.items() if c < 5)
    common_words = set(w for w,c in word_count.items() if c >= 5)

    def replace_word_node(node):
        for idx,n in enumerate(node[1:]):
            if type(n) is list:
                replace_word_node(n)
            else:
                if n in rare_words:
                    node[idx+1] = '_RARE_'
        return node

    new_parse_data = []
    with open(outputname, 'w') as wf:
        for d in parse_data:
            wf.write(json.dumps(replace_word_node(d))+"\n")
            
def CYK_parsing(trainFileRare, parse_filename, prediction_filename):
    unaryrule = {}
    binaryrule = {}
    nonterminal = {}

    os.system("python2.7 count_cfg_freq.py "+ trainFileRare +"> cfg.counts")
    
    word_count = defaultdict(int)
    def word_count_node(node):
        for n in node[1:]:
            if type(n) is list:
                word_count_node(n)
            else:
                word_count[n] += 1

    parse_data = []
    with open("parse_train.dat") as f:
        for line in f:
            parsed = json.loads(line.strip()) 
            parse_data.append(parsed)
            word_count_node( parsed )
    rare_words = set(w for w,c in word_count.items() if c < 5)
    common_words = set(w for w,c in word_count.items() if c >= 5)
    
    with open('cfg.counts') as f:
        for line in f:
            line = line.strip()
            try:
                splitted_line = line.split(' ')
                count = splitted_line[0]
                _type = splitted_line[1]
                if _type == 'UNARYRULE':
                    tag = splitted_line[2]
                    word = splitted_line[3]
                    if tag not in unaryrule:
                        unaryrule[tag] = {}
                    unaryrule[tag][word] = int(count)
                elif _type == 'BINARYRULE':
                    tag1 = splitted_line[2]
                    tag2 = splitted_line[3]
                    tag3 = splitted_line[4]
                    if tag1 not in binaryrule:
                        binaryrule[tag1] = {}
                    binaryrule[tag1][tag2,tag3] = int(count)
                elif _type == 'NONTERMINAL':
                    tag = splitted_line[2]
                    nonterminal[tag] = int(count)
            except:
                print(line)

    binary_param = {}
    unary_param = {}

    def binary_param_calculate(tag1, tag2, tag3):
        return log(binaryrule[tag1][(tag2, tag3)]/nonterminal[tag1])

    def unary_param_calculate(tag, word):
        return log(unaryrule[tag][word]/nonterminal[tag])

    for tag1 in binaryrule:
        binary_param[tag1] = {}
        for tag2,tag3 in binaryrule[tag1]:
            binary_param[tag1][tag2,tag3] = binary_param_calculate(tag1, tag2, tag3)

    for tag in unaryrule:
        unary_param[tag] = {}
        for word in unaryrule[tag]:
            unary_param[tag][word] = unary_param_calculate(tag, word)

    def CYK(binary_param, unary_param, sentence):
        sentence = sentence.strip().split(" ")
        n = len(sentence)

        pi = {}
        bp = {}

        for i in range(1, n+1):
            word = sentence[i-1]
            if word not in common_words:
                word = "_RARE_"
            for tag in nonterminal.keys():
                if tag in unary_param and word in unary_param[tag]:
                    pi[i,i,tag] = unary_param[tag][word]
                else:
                    pi[i,i,tag] = float("-inf")

        def possible_tags(tag):
            if tag in binary_param:
                return binary_param[tag].keys()
            else:
                return []

        try:
            for l in range(1, n):
                for i in range(1, n-l+1):
                    j = i+l
                    for x in nonterminal.keys():
                        pi[i,j,x], bp[i,j,x] = max([(binary_param_calculate(x,y,z) + pi[i,s,y] + pi[s+1,j,z], (y,z,s)) 
                                                        for y,z in possible_tags(x) for s in range(i, j)]+[(float("-inf"),(0,0,0))]
                                                   ,key=lambda x: x[0])
        except:
            raise

        bp_final = None
        if pi[1,n,'S'] != float("-inf"):
            bp_final = 'S'
        else:
            _, bp_final = max(((pi[1,n,x], x) for x in nonterminal.keys()),key=lambda x: x[0])

        def build(start,end,tag):
            if start != end:
                left_tag, right_tag, split_point = bp[start,end,tag]
                return [tag, build(start,split_point,left_tag), build(split_point+1,end,right_tag)]
            else:
                return [tag, sentence[start-1]]

        return json.dumps(build(1, n, bp_final))

    with open(parse_filename) as f:
        with open(prediction_filename,'w') as wf:
            for l in f:
                wf.write(CYK(binary_param, unary_param, l)+"\n")
