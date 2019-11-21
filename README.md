# hw3

## Group members

Linxuan Xu

Hui Yang

## Explanation on the flags:

Usage: `python3 ekcc.py [-emit-ast|-emit-llvm] -o /path/to/output/file /path/to/input/file`

With `-emit-ast` flag on, the program will write the AST generated in YAML format into output file.

With `-emit-llvm` flag on, the program will write the LLVM IR into output file.

`-o` flag defines the place of output. In case where the output is not specified, the AST tree would be in standard output.

## How to Run
### Step 1: Install dependency packages
```
$ pip3 install -r requirements.txt 
```

### Step 2: Enter the directory that contains /bin/ekcc.py. Run the following line to check whether 
```
$ python3 ekcc.py -emit-ast -o /path/to/output/file /path/to/input/file
```

For example:

case 1:
`
$ python3 ekcc.py -emit-ast -o ./out/out.yml ./test_files/test1.ek
`

The command line is parsing ./test_files/test1.ek into an AST tree. The result would be in ./out/out.yml

case 2:
`
$ python3 ekcc.py -emit-llvm ./test_files/test1.ek
`

The command line is parsing ./test_files/test1.ek into LLVM IR. The result would be in the standard output
