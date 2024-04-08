from typing import List

import openai
import re, json

from model.question import Question

MODEL = "gpt-3.5-turbo"


def complete_text(prompt: str) -> str:
    """
    Complete text using GPT-3.5 Turbo
    :param prompt: Prompt to complete
    :return: Completed text
    """
    example_json = {
       "questions": 
        [
            {
                "question": "  What is the value of sin(90 degrees)?",
                "answers": [
                    "1",
                    "0",
                    "-1",
                    "Undefined"
                ],
                "correct_answer": "Undefined"
            }
         ]
    }

    chat_completion = openai.ChatCompletion.create(
        model=MODEL,
        response_format={"type":"json_object"},
        messages=[
            {"role":"system","content":"Provide output in valid JSON. The data schema should be like this: "+json.dumps(example_json)},
            {"role":"user","content":prompt}
        ]
    )

    return chat_completion["choices"][0]["message"]["content"]

    #messages = [{"role": "user", "content": prompt}]
    #return openai.ChatCompletion.create(model=MODEL, messages=messages)["choices"][0]["message"]["content"]


def prepare_prompt(topics: str, number_of_questions: int, number_of_answers: int) -> str:
    """
    Prepare prompt to complete
    :param topics: Topics to include in the exam
    :param number_of_questions: Number of questions
    :param number_of_answers: Number of answers
    :return: Prompt to complete
    """
    return (
        f"Provide valid JSON output."
        f"Create an exam of multiple choice questions with {number_of_questions} "
        f"questions and {number_of_answers} of possible answers in each question. "
        f"The exam should be about {topics}. Only generate the questions and "
        f"answers, not the exam itself."
        #f"Every element in json should only have question tag and answers tag. "
        #f"answers should be a list with the correct answer surrounded by ** in its orginal spot."
    )


def sanitize_line(line: str, is_question: bool) -> str:
    """
    Sanitize a line from the response
    :param line: Line to sanitize
    :param is_question: Whether the line is a question or an answer
    :return: Sanitized line
    """
    if is_question:
        new_line = re.sub(r"[0-9]+.", " ", line, count=1)
    else:
        new_line = re.sub(r"[a-eA-E][).]", " ", line, count=1)

    return new_line


def get_correct_answer(answers: List[str]) -> int:
    """
    Return the index of the correct answer
    :param answers: List of answers
    :return: Index of the correct answer if found, -1 otherwise
    """
    for index, answer in enumerate(answers):
        if answer.count("**") > 0:
            return index

    return -1


def response_to_questions(response: str) -> List[Question]:
    """
    Convert the response from the API to a list of questions
    :param response: Response to convert
    :return: List of questions
    """
    questions = []
    count = 1

    #for question_text in response.split("\n\n"):
    #    #print(question_text)
    #    question_text = question_text.strip()

    #    if not question_text:
    #        continue

    #    question_lines = question_text.splitlines()

    #    question = sanitize_line(question_lines[0], is_question=True)
    #    answers = list(map(lambda line: sanitize_line(line, is_question=False), question_lines[1:]))

    #    correct_answer = get_correct_answer(answers)
    #    answers[correct_answer] = answers[correct_answer].replace("**", "")

    #    answers = list(map(lambda answer: answer.strip(), answers))

    #    questions.append(Question(count, question, answers, correct_answer))

    #    count += 1

    #print(response)
    data = json.loads(response)
    # Extract questions and answers

    questions = []

    for item in data['questions']:
        question_text = item['question']
        answers = item['answers']
        # Extract correct answer
        #correct_answer = [answer.strip('**') for answer in answers if answer.startswith('**')]
        # Append question and correct answer to the list
        #correct_answer = get_correct_answer(answers)
        correct_answer = item['correct_answer']
        correct_answer = answers.index(correct_answer)

        print("Question -->", question_text)
        print("Answer --> ", str(answers))
        print("Correct Answer --> ", str(correct_answer))

        questions.append(Question(count, question_text, answers, correct_answer))
        count +=1 

    return questions


def get_questions(topics: str, number_of_questions: int, number_of_answers: int) -> List[Question]:
    """
    Get questions from OpenAI API
    :param topics: Topics to include in the exam
    :param number_of_questions: Number of questions
    :param number_of_answers: Number of answers
    :return: List of questions
    """
    #print(topics)
    #print(number_of_answers)
    #print(number_of_questions)
    prompt = prepare_prompt(topics, number_of_questions, number_of_answers)
    #print(prompt)
    response = complete_text(prompt)
    #print(response)
    #print("************************************************************************************************")
    return response_to_questions(response)


def complete_text_for_clarification(prompt: str) -> str:
    """
    Complete text using GPT-3.5 Turbo
    :param prompt: Prompt to complete
    :return: Completed text
    """

    messages = [{"role": "user", "content": prompt}]

    return openai.ChatCompletion.create(model=MODEL, messages=messages)["choices"][0]["message"]["content"]



def clarify_question(question: Question) -> str:
    """
    Clarify a question using GPT-3.5 Turbo
    :param question: Question to clarify
    :return: Text clarifying the question
    """
    join_questions = "\n".join([f"{chr(ord('a') + i)}. {answer}" for i, answer in enumerate(question.answers)])

    prompt = f"Given this question: {question.question}\n"
    prompt += f" and these answers: {join_questions}\n\n"
    prompt += f"Why the correct answer is {chr(ord('a') + question.correct_answer)}?\n\n"

    #print(prompt)
    return complete_text_for_clarification(prompt)
