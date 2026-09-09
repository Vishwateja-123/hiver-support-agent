.PHONY: test demo audit
test:
	python3 -m unittest discover -s tests -v
demo:
	python3 -m support_agent evaluate --train data/demo/train.jsonl --test data/demo/test.jsonl --out results/demo
audit:
	python3 -m support_agent audit --data data/demo
