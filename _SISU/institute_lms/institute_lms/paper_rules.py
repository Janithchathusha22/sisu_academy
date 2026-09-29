"""Assessment validation and deterministic marking, independent of the UI."""
from .pricing_rules import integer

def validate_questions(rows):
    if not isinstance(rows,list) or not 1<=len(rows)<=100: raise ValueError('Add between 1 and 100 questions')
    result=[]
    for row in rows:
        if not isinstance(row,dict): raise ValueError('Invalid question')
        kind=row.get('kind'); prompt=str(row.get('prompt','')).strip()
        if kind not in ('MCQ','True/False','Written') or not prompt or len(prompt)>3000: raise ValueError('Each question needs a type and prompt (maximum 3,000 characters)')
        marks=integer(row.get('marks',1),'Marks',100)
        if marks<1: raise ValueError('Marks must be positive')
        options=row.get('options',[])
        if kind=='True/False': options=['True','False']
        if kind=='Written': options=[];answer=None
        else:
            if not isinstance(options,list) or not 2<=len(options)<=5 or any(not isinstance(x,str) or not x.strip() or len(x)>500 for x in options): raise ValueError('Use 2–5 nonempty options, each at most 500 characters')
            if len(set(x.strip().casefold() for x in options))!=len(options): raise ValueError('Answer options must be distinct')
            answer=integer(row.get('answer'),'Correct option',len(options)-1)
        result.append({'kind':kind,'prompt':prompt,'options':options,'answer':answer,'marks':marks})
    return result

def public_questions(rows):
    return [{k:v for k,v in r.items() if k!='answer'} for r in rows]

def grade(rows,answers):
    if not isinstance(answers,list) or len(answers)!=len(rows): raise ValueError('Submit one answer per question')
    total=0;manual=False
    for q,a in zip(rows,answers):
        if q['kind']=='Written':
            if not isinstance(a,str) or len(a)>10000: raise ValueError('Written answers are limited to 10,000 characters')
            manual=True
        elif a is not None:
            choice=integer(a,'Answer',len(q['options'])-1)
            if choice==q['answer']:total+=q['marks']
    return total,manual
