import unittest
from institute_lms.pricing_rules import calculate
from institute_lms.paper_rules import validate_questions, public_questions, grade

class AssignedPricing(unittest.TestCase):
    def test_included_seats_and_extra_units(self):
        self.assertEqual(calculate(10000,500,50,500)['total_minor'],10000)
        self.assertEqual(calculate(10000,500,50,503)['total_minor'],10150)
        self.assertEqual(calculate(10000,500,50,0)['total_minor'],10000)
    def test_discount_before_tax_and_half_up(self):
        q=calculate(10001,0,0,1,1000,2000)
        self.assertEqual(q['discount_minor'],1000)
        self.assertEqual(q['tax_minor'],1800)
        self.assertEqual(q['total_minor'],10801)
        self.assertEqual(calculate(1,0,0,1,5000)['discount_minor'],1)
    def test_explicit_free_contract(self):
        self.assertEqual(calculate(0,0,0,1)['total_minor'],0)
    def test_negative_fractional_boolean_and_overflow_rejected(self):
        for value in (-1,1.5,True,'NaN','1e3','١'):
            with self.assertRaises(ValueError):calculate(value,0,0,1)
        with self.assertRaises(ValueError):calculate(2000000000,0,1,1)
        with self.assertRaises(ValueError):calculate(100,0,0,1,10001)

class PaperRules(unittest.TestCase):
    def setUp(self):
        self.questions=validate_questions([
            {'kind':'MCQ','prompt':'2 + 2?','options':['3','4','5','6'],'answer':1,'marks':2},
            {'kind':'True/False','prompt':'4 is even','answer':0,'marks':1},
            {'kind':'Written','prompt':'Explain your method','marks':3},
        ])
    def test_student_payload_never_has_answer_keys(self):
        self.assertTrue(all('answer' not in row for row in public_questions(self.questions)))
        self.assertEqual(self.questions[0]['answer'],1)
    def test_marking_excludes_written_answers_until_review(self):
        self.assertEqual(grade(self.questions,[1,0,'My explanation']),(3,True))
        self.assertEqual(grade(self.questions,[None,1,'']),(0,True))
    def test_invalid_and_duplicate_options_are_rejected(self):
        for q in ({**self.questions[0],'answer':4},{**self.questions[0],'marks':0},{**self.questions[0],'options':['Yes',' yes ']}):
            with self.assertRaises(ValueError):validate_questions([q])
    def test_invalid_submissions_and_injected_score_are_rejected(self):
        with self.assertRaises(ValueError):grade(self.questions,[True,0,''])
        with self.assertRaises(ValueError):grade(self.questions,[1,0,'x'*10001])
        with self.assertRaises(ValueError):grade(self.questions,{'score':100})
        with self.assertRaises(ValueError):grade(self.questions,[1])
    def test_multilingual_prompts_preserved(self):
        row={**self.questions[0],'prompt':'ගණිතය · கணிதம் · الرياضيات'}
        self.assertEqual(validate_questions([row])[0]['prompt'],row['prompt'])
