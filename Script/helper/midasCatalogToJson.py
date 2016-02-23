#!/usr/bin/env python

import json
import argparse
import sys


def main(argv=None):
  if argv is None:
    argv = sys.argv
  parser = argparse.ArgumentParser(
          prog=argv[0],
          description=__doc__
  )
  parser.add_argument('-i', "--input", required=True, help="Input Catalog")
  parser.add_argument('-o', "--output", required=True, help="Output json")
  parser.add_argument('-s', "--suffix", help="suffix to sort data types")
  parser.add_argument('-u', "--url", required=True, help="url where to download the data from")
  args = parser.parse_args(argv[1:])
  f = open(args.input,'r')
  loaded_file = f.read().splitlines()
  suffix = args.suffix
  if suffix == None:
    suffix = ''
  print suffix
  all_dict = {}
  all_dict['files']={}
  for line in loaded_file:
    if "ID=" in line and "name=" in line and 'format="image/ITK"' in line:
      split_line = line.split(" ")
      for item in split_line:
        if "ID=" in item:
          current_id = item.split('=')[1]
          current_id = current_id.replace('"','' )
        if "name=" in item:
          current_name = item.split('=')[1]
          current_name = current_name.replace('"','')
      if suffix in current_name:
        all_dict['files'][current_name] = current_id
    with open(args.output, 'w') as f:
      all_dict[ 'url' ] = args.url
      json.dump(all_dict, f)
  

if __name__ == "__main__":
  sys.exit(main())


