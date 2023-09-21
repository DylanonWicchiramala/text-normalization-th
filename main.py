# -*- coding: utf-8 -*-
import argparse

def get_arguments():
    """
    Get input arguments main routine

    
    Parameters
    ----------
    -
    Return
    ------
    Input argument -> args.XX
    """
    parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')

    # Add arguments
    parser.add_argument('-i', '--input_file', type=str, help='input file', required=True, default=None)
    parser.add_argument('-o', '--output_file', type=str, help='input file. example: ./pathtofile/text_file.txt', required=False, default=None)
    parser.add_argument('-u', '--use_multiprocessing', type=bool, help='Use multiprocess to compute.', choices=[True, False], required=False, default=False)
    parser.add_argument('-n', '--num_proc', type=int, help='define numprocessor to Use multiprocess. if =0 use all processor', required=False, default=-1)

    return parser.parse_args()

argv = get_arguments()

import os
import multiprocessing
import sys
import re
from pythainlp import util, tokenize
from functools import wraps


"""## util function"""
def find_inspect(regex: str, text: str, st: int=50, ed=50 , min=None,max=None):
    ind = [match.start() for match in re.finditer(regex, text, flags=re.IGNORECASE)]
    ind = ind[min:max]
    for i in ind:
        print(text[i-st:i+ed])
    return ind

def save(s:str, path:str='text_file.txt'):
    '''save string s into patd dir.
    '''
    with open(path, "w", encoding="utf-8") as f:
        # Write the string to the file
        f.write(s)
    print(f'File save at {path}')


"""## function for normalize"""
def strorlist_map(func, iter: str or list[str]):
    '''
    return:
    if input is string return func(map)
    else, if input is iterable object return list of map object
    '''
    # check input text is list or iterable object
    if isinstance(iter, str):
        return func(iter)
    elif hasattr(iter, '__iter__'):
        return list( map(lambda i: func(i), iter) )
    else:
        raise TypeError(f"input {type(text)} are not ether str or iterable object")

def vowel_normalize(text: str or list[str]):
    '''
    input: list of string of string 
    output: list of string or string
    normalize เ เ, ํ า, double of same vowel(such as โโ, แแ,  ูู, ุุ ,่่) , and wrong order of vowel and tonal(such as ก่ิง)
    '''
    return strorlist_map(util.normalize, text)

def thai_digit_to_arabic_digit(text: str or list[str]):
    '''
    input: list of string of string 
    output: list of string or string
    change thai digit(๑๒๓๔) to string of arabic digit
    
    example:
        thai_digit_to_arabic_digit('๑๒๓๔กขคabc') -> '1234กขคabc'
    '''
    return strorlist_map(util.thai_digit_to_arabic_digit,text)


"""### symbol normalize"""
def symbol_normalization(text: str or list):
    '''
    change symbol to speak language 
    example '2=2' -> 2เท่ากับ2
    '''
    types = [
        ['฿','\$','£','€','='],
        '³²',
        ['\+','\*'],
        '&'
    ]
    speak_map = {
        '฿' : ['', 'บาท'] ,    
        '\$' : ['', 'ดอลล่าร์'] , 
        '£' : ['', 'ปอนด์'] ,   
        '€' : ['', 'ยูโร'] ,  
        '=' : ['','เท่ากับ'] , #ต้องไม่ติดกับตัวมันเอง types[0]

        '%' : ['เปอร์เซ็นต์'] ,
        '÷' : ['หาร'] ,
        '±' : ['บวกลบ'] ,
        '¾' : ['สามส่วนสี่'] ,
        '½' : ['หนึ่งส่วนสอง'] ,
        '¼' : ['หนึ่งส่วนสี่'] ,

        '³' : ['','ยกกำลังสาม'] ,
        '²' : ['','ยกกำลังสอง'] , #หลังตัวเลข types[1]

        '\+' : ['', 'บวก'] ,
        '\*' : ['', 'คูณ'] , #อยู่ระหว่างตัวเลข types[2]
        
        '&' : ['', 'และ', ' and '] , #อยู่ระหว่างภาษา types[3]
    } 
    def _strip_accents(text):
        return ''.join(char for char in
                   unicodedata.normalize('NFKD', text)
                   if unicodedata.category(char) != 'Mn')


    def _symbol_normalization(text:str):
        for sym in types[0]:
            re_rule = sym + r'{2,}'    #${2,}
            text = re.sub(re_rule, '', text)
            text = re.sub(sym, speak_map[sym][1], text)

        for sym in types[1]:
            re_rule = f'([0-9])({sym})'
            text = re.sub(re_rule, r'\1'+speak_map[sym][1] , text)
        
        for sym in types[2]:
            re_rule = f'([0-9][ ]?)({sym})([ ]?[0-9])'
            text = re.sub(re_rule, r'\1'+speak_map[sym][1]+r'\3', text )

        for sym in types[3]:
            re_rules = [
                f'([ก-ฮ|ะ-ู|เ-์][ ]?)({sym})([ ]?[ก-ฮ|ะ-ู|เ-์])',
                f'([a-z|A-Z][ ]?)({sym})([ ]?[a-z|A-Z])',
                f'([a-z|A-Z][ ]?)({sym})([ ]?[ก-ฮ|ะ-ู|เ-์])',
                f'([ก-ฮ|ะ-ู|เ-์][ ]?)({sym})([ ]?[a-z|A-Z])',
            ]
            text = re.sub(re_rules[0], r'\1'+speak_map[sym][1]+r'\3', text )
            text = re.sub(re_rules[1], r'\1'+speak_map[sym][2]+r'\3', text )
            text = re.sub(re_rules[2], r'\1'+speak_map[sym][2]+r'\3', text )
            text = re.sub(re_rules[3], r'\1'+speak_map[sym][2]+r'\3', text )

        for sym ,val in speak_map.items():
            if len(val)==1:
                text = re.sub(sym,val[0],text)

        return text
    
    return strorlist_map(_symbol_normalization, text)


"""### number normalize"""
def _comma_sperate_number_to_word(inp_number:str or re.Match)->str:
    '''
    input: an comma sperate number string

    example:
        _comma_sperate_number_to_word('03,343.315') -> 'สามพันสามร้อยสี่สิบสามจุดสามหนึ่งห้า'
        _comma_sperate_number_to_word('3,400') -> 'สามพันสี่ร้อย'
        _comma_sperate_number_to_word('23.55') -> 'ยี่สิบสามจุดห้าห้า'
        _comma_sperate_number_to_word('23.') ->  'ยี่สิบสาม'
        _comma_sperate_number_to_word('0.30000') -> 'ศูนย์จุดสาม'
    '''
    if isinstance(inp_number, re.Match):
        inp_number = inp_number.group()

    # delete other character.
    number = re.sub(r'[^\d\,\.]','',inp_number)
    
    # default number for decimal and p
    p = ''
    decimal = ''

    # if '.' in number string.
    num_parts = tuple(number.split('.'))
    if len(num_parts)==2:
        number, decimal  = num_parts

        # delete 0 after decimal number (.30 -> .3)
        decimal = str(float( '.'+decimal ))[2:]

        # if have number after '.'
        if re.search(r'[\d]',decimal):
            p = 'จุด'
    elif len(num_parts)>2:
        return inp_number
    

    #remove non-number charactor
    number = re.sub(r'[^\d]+','', number)
    number = int(number)

    return util.num_to_thaiword(number) + p + util.digit_to_text(decimal)


def _tel_number_to_word(number:str or re.Match)->str:
    '''
    input: string of telephone number
    return: string

    example:
        _tel_number_to_word('000-000-0000') -> 'ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์'
        _tel_number_to_word('000 000 0000') -> 'ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์ศูนย์'
    '''
    if isinstance(number, re.Match):
        number = number.group()

    # delete other character.
    number = re.sub(r'[^\d\-\ ]','',number)

    number = re.sub(r'[^\d]+','', number)
    return util.digit_to_text(number)


def _time_to_word_old(inp_time:str or re.Match)->str:
    '''
    input: string of time with format ss:mm:hh mm:hh ss.mm.hh
    return: string

    example:
        _time_to_word('01:23:45') -> 'หนึ่งนาฬิกายี่สิบสามนาทีสี่สิบห้าวินาที'
        _time_to_word('10:00') -> 'สิบนาฬิกา'
        _time_to_word('00.00.21') -> 'ยี่สิบสี่นาฬิกายี่สิบเอ็ดวินาที'
    '''
    if isinstance(inp_time, re.Match):
        inp_time = inp_time.group()

    # delete other character.
    time = re.sub(r'[^\d\.\:]+','',inp_time)

    # split time string into hours, minutes and seconds
    time_parts = time.split(':') if ':' in time else time.split('.')
    # change time parts into int
    time_parts = list(map(int, time_parts))

    if len(time_parts) == 2:
        hour, minute = time_parts
        second = 0
    elif len(time_parts) == 3:
        hour, minute, second,  = time_parts
    else:
        return inp_time

    # check is it time
    if (hour>24 or minute>60 or second>60):
        return inp_time

    # convert hours, minutes and seconds to words
    hour = 24 if hour==0 else hour
    hour_word = util.num_to_thaiword(hour)
    minute_word = util.num_to_thaiword(minute) if minute>0 else ''
    second_word = util.num_to_thaiword(second) if second>0 else ''

    # generate result string
    result = ''
    if hour_word:
        result += hour_word + 'นาฬิกา'
    if minute_word:
        result += minute_word + 'นาที'
    if second_word:
        result += second_word + 'วินาที'

    return result


def _time_to_word(inp_time:str or re.Match)->str:
    '''
    input: string of time with format ss:mm:hh mm:hh ss.mm.hh
    return: string

    example:
        _time_to_word('01:23:45') -> 'หนึ่งนาฬิกายี่สิบสามนาทีสี่สิบห้าวินาที'
        _time_to_word('10:00') -> 'สิบนาฬิกา'
        _time_to_word('00.00.21') -> 'ยี่สิบสี่นาฬิกายี่สิบเอ็ดวินาที'
    '''
    if isinstance(inp_time, re.Match):
        inp_time = inp_time.group()

    # delete other character.
    time = re.sub(r'[^\d\.\:]+','',inp_time)

    # replace '.' to ':'
    time = re.sub(r'\.', ':', time)

    #check if it is time format
    try:
        time_word = util.time_to_thaiword(time)
    except ValueError:
        return inp_time

    return time_word


def _date_to_word(inp_date:str or re.Match)->str:
    '''
    input: string of date with format dd-mm-yyyy dd/mm/yyyy dd.mm.yyyy  
    return: string

    example: 
        _date_to_word('12.12.90') -> 'สิบสองเดือนสิบสองปีเก้าศูนย์'
        _date_to_word('31/1/2556') -> 'สามสิบเอ็ดเดือนหนึ่งปีสองพันห้าร้อยห้าสิบหก'
    '''
    if isinstance(inp_date, re.Match):
        inp_date = inp_date.group()

    # delete other character.
    date = re.sub(r'[^\d\-\./]+','',inp_date)
    
    # replace date seperator
    date = re.sub(r'[\-\./]+','<sep>',date)

    # split date into day, month, and year
    date_parts = date.split('<sep>')
    if len(date_parts) == 3:
        day, month, year = map(int, date_parts)
    else:
        return inp_date

    # convert day to Thai word
    if day > 0 and day <= 31:
        day_str = util.num_to_thaiword(day)
    else:
        return inp_date

    # convert month to Thai word
    # if month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
    #     month_str = MONTHS_TH[month-1]
    if month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
        month_str = 'เดือน'+ util.num_to_thaiword(month)
    else:
        return inp_date

    # convert year to Thai word
    if year < 100:
        year_str = 'ปี' + util.digit_to_text(str(year))
    else:
        year_str = 'ปี' + util.num_to_thaiword(year)

    return day_str + month_str + year_str



def digit_to_word(text:str or list(str)):
    ''' 
    input: text or list of text 
    return: text of list of text which change (string of) number digit into thai word according to the below condition.
    example : 2,400.90 -> สองพันสี่ร้อยจุดเก้าสิบ
            21.00 -> ยี่สิบเอ็ด
            094-XXX-XXXX -> ศูนย์เก้าสี่xxxxxxxx
            23-09-2002 -> ยี่สิบสามเดือนเก้าปีสอง

    case ที่ไม่ต้องอ่านหลัก
    - tel number
    - 0 นำหน้า
    - digit > 8

    case ที่ต้องอ่านหลัก
    - time  xx:xx:xx xx:xx xx.xx.xx
    - comma sperate number xx.xx  x,xxx.xx  xx,xxx x.00 
    - date xx-xx-xxxx xx/xx/xxxx  xx.xx.xxxx   xx <เดือน> xxxx
    - อื่นๆ
    '''


    def _digit_to_word(text:str):
        tmp = {
            're_month' : r'มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม|ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.',
            're_tel0' : r'\b[0-9]{2,3}[-][0-9]{3,4}[-][0-9]{4}\b',
            're_tel1' : r'\b[0-9]{2,3}[ ][0-9]{3,4}[ ][0-9]{4}\b',
        }
        __regex = {
            'comma_separated_number' : re.compile(r'([-]?(?!0\d)(\d{1,3}(,\d{3})+)(\.\d+)?)|((?!0\d)\d{1,3}\.\d+)'),     # XX,XXX.XX  XX.XX
            'date' : re.compile(r'[0-3]?\d{1}[\/\-\.][0|1]?[\d][\/\-\.][1|2]\d{3}'),                                      # XX/XX/XXXX  XX-XX-XXXX  XX.XX.XXXX
            'time' : re.compile(r'((\d{1,2})[:.](\d{2}))[ ]?[นาฬิกา|น]?'),
            'tel_number' : re.compile( tmp['re_tel0'] + "|" + tmp['re_tel1']),
            'leading_zero' : re.compile(r'\b0\d+\b'),
            'more_than_8digit' : re.compile(r'\d{9,}'),
            'other' : re.compile(r'\d+')
        }

        # function to handdle each format type
        tmp_func_list = [
            _comma_sperate_number_to_word,
            _date_to_word,
            _time_to_word,
            _tel_number_to_word,
            lambda txt: util.digit_to_text(txt.group()),
            lambda txt: util.digit_to_text(txt.group()),
            lambda txt: util.num_to_thaiword(int(txt.group()))
        ]
        __func = dict(zip( __regex.keys(), tmp_func_list ))

        del tmp, tmp_func_list

        for key in __regex.keys():
            # find index 
            text = __regex[key].sub(__func[key], text)

        return text

    return strorlist_map(_digit_to_word, text)


"""### symbol remove"""
def symbol_remove(text: str or list):
    re_symbol = '[^ก-๛a-zA-Z ]'
    sym_remove = lambda text: re.sub(re_symbol, '', text)
    return strorlist_map(sym_remove, text)


"""### tokenize and maiyamok"""
def word_tokenize(text:str or list(str), engine:str='newmm'):
    def _word_tokenize(text:str, engine:str=engine):
        toklist = tokenize.word_tokenize(text, engine=engine, keep_whitespace=False)
        # normalize maiyamok
        toklist = util.maiyamok(toklist)
        return ' '.join(toklist)
    return strorlist_map(_word_tokenize, text)


"""# Main function"""
__path__ = os.getcwd().replace('\\','/')

use_multiprocessing = argv.use_multiprocessing
numproc = (multiprocessing.cpu_count() if argv.num_proc == -1 else argv.num_proc )if use_multiprocessing else 1

# get text data from argument
path = argv.input_file

file = open(path, 'r', encoding='utf-8')
raw_text = file.read()


text_list = raw_text.split('\n')

fun_list = [
    vowel_normalize,
    thai_digit_to_arabic_digit,
    symbol_normalization,
    digit_to_word,
    symbol_remove,
    word_tokenize,
]

def pipeline(txt: dict, func: list=fun_list):
    txt = txt['text']
    for f in func:
        txt = f(txt)
    return {'text': txt}

from datasets import Dataset
import datasets

dataset = Dataset.from_dict({'text':text_list})
# dataset = dataset.flatten_indices()

norm_dataset = dataset.map(pipeline , num_proc=numproc)
final_text = ' '.join(norm_dataset['text'])

o_path = __path__ + "/output.txt" if argv.output_file is None else argv.output_file
save(final_text, o_path)