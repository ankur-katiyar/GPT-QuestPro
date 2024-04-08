import os, re, json
from datetime import datetime
from abc import abstractmethod
from typing import Optional

import streamlit as st

from model.question import Question
from utils.api import get_questions, clarify_question
from utils.generate_document import questions_to_pdf

class PageEnum:
    """
    Enum for pages
    """
    GENERATE_EXAM = 0
    QUESTIONS = 1
    RESULTS = 2
    QUESTION_BROWSE = 3
    EDIT_JSON = 4


class Page:

    @abstractmethod
    def render(self, app):
        """
        Render the page (must be implemented by subclasses)
        """


class GenerateExamPage(Page):

    description = """
    This app generates exams with questions and answers for Samar baby, created by Papa.
    """
    prompt = """
    An example of a prompt: Develop a challenging 9th-grade math test covering trigonometry, algebra, quadratics, and logic puzzles, fractions, percentages, geometry. 
    Include multiple-choice questions testing understanding and problem-solving skills. 
    Aim to stimulate critical thinking and application of mathematical concepts.
    """

    def render(self, app):
        """
        Render the page
        """
        st.title("Generate exam")

        st.markdown(self.description)
        st.markdown(self.prompt)

        topics = st.text_input(
            "Topics",
            placeholder="Topics to include in the exam",
            help="It is recommended to use a comma-separated list of topics"
        )

        number_of_questions = st.number_input(
            "Number of questions",
            min_value=5,
            max_value=30,
            value=10,
            help="Number of questions that will be generated"
        )

        number_of_answers = st.number_input(
            "Number of answers",
            min_value=3,
            max_value=5,
            value=4,
            help="Number of possible answers that will be generated for each question"
        )

        if st.button("Browse Questions", help="Load from earlier generated questions"):
                    app.change_page(PageEnum.QUESTION_BROWSE)

        if st.button("Edit Questions", help="Edit previously generated questions"):
                    app.change_page(PageEnum.EDIT_JSON)

        if st.button("Generate", help="Generate the questions according to the parameters"):

            st.warning("Generating questions. This may take a while...")
            try:
                app.questions = get_questions(topics, number_of_questions, number_of_answers)
            except Exception as e:
                print(e)
                st.error("An error occurred while generating the questions. Please try again")

        if app.questions is not None:

            st.info(
                f"An exam with {len(app.questions)} questions has been generated. You "
                f"can download the questions as a PDF file or take the exam in the app."
            )

            #print(app.questions)
            myq=MyQuestion()
            myq.write_json(app,topics)

            left, center, right = st.columns(3)

            with left:

                questions_to_pdf(app.questions, "questions.pdf")
                st.download_button(
                    "Download",
                    data=open("questions.pdf", "rb").read(),
                    file_name="questions.pdf",
                    mime="application/pdf",
                    help="Download the questions as a PDF file"
                )

            with right:
                if st.button("Start exam", help="Start the exam"):
                    app.change_page(PageEnum.QUESTIONS)


class QuestionsPage(Page):

    def __init__(self):
        self.number_of_question = 0

    def render(self, app):
        """
        Render the page
        """
        st.title("Questions")

        question = app.questions[self.number_of_question]

        answer = self.__render_question(question, app.get_answer(self.number_of_question))

        app.add_answer(self.number_of_question, answer)

        left, center, right = st.columns(3)

        if self.number_of_question != 0:
            with left:
                if st.button("Previous", help="Go to the previous question"):
                    self.__change_question(self.number_of_question - 1)

        with center:
            if st.button("Finish", help="Finish the exam and go to the results page"):
                app.change_page(PageEnum.RESULTS)

        if self.number_of_question != len(app.questions) - 1:
            with right:
                if st.button("Next", help="Go to the next question"):
                    self.__change_question(self.number_of_question + 1)

    @staticmethod
    def __render_question(question: Question, index_answer: Optional[int]) -> int:
        """
        Render a question and return the index of the answer selected by the user
        :param question: Question to render
        :param index_answer: Index of the answer selected by the user (if any)
        :return: Index of answer selected by the user
        """
        if index_answer is None:
            index_answer = 0

        #st.write(f"**{question.id}. {question.question}**")
        st.write(f"{question.id}. {question.question}")
        
        answer = st.radio("Answer", question.answers, index=index_answer)

        index = question.answers.index(answer)

        return index

    def __change_question(self, index: int):
        """
        Change the current question and rerun the app
        :param index: Index of the question to change to
        """
        self.number_of_question = index
        #st.experimental_rerun()
        st.rerun()

import configparser
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email(app, num_correct):
    # Email configuration
    config = configparser.ConfigParser()
    config.read('config.ini')

    sender_email      = config['Email']['sender_email']
    sender_password   = config['Email']['sender_password']
    receiver_email    = config['Email']['receiver_email']

    print(sender_email)
    print(sender_password)
    print(receiver_email)

    subject = "Result Summary"
    
    # Create message container
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    message=""
    if app.exam:
        message = f"Exam Attempted: {app.exam}" + "\n"
    message = message + f"Number of questions: {len(app.questions)}" + "\n" 
    message = message + f"Number of correct answers: {num_correct}" + "\n"
    message = message + f"Percentage of correct answers: {num_correct / len(app.questions) * 100:.2f}%" 
    
    # Add text body to the email
    msg.attach(MIMEText(message, 'plain'))
    context = ssl.create_default_context()
    # Send email
    try:
        mailserver = smtplib.SMTP('smtp.gmail.com',587)
        # identify ourselves to smtp gmail client
        mailserver.ehlo()
        # secure our email with tls encryption
        mailserver.starttls(context=context)
        # re-identify ourselves as an encrypted connection
        mailserver.ehlo()
        mailserver.login(sender_email, sender_password)
        mailserver.sendmail(sender_email,receiver_email,msg.as_string())
        mailserver.quit()        
        st.success("Email sent successfully!")
    except Exception as e:
        st.error(f"Failed to send email. Error: {str(e)}")

class ResultsPage:

    def __init__(self):
        self.clarifications = {}

    def render(self, app):
        """
        Render the page
        """
        st.title("Results")

        num_correct = self.__get_correct_answers(app)

        st.write(f"### Number of questions: {len(app.questions)}")
        st.write(f"### Number of correct answers: {num_correct}")
        st.write(f"### Percentage of correct answers: {num_correct / len(app.questions) * 100:.2f}%")

        if st.button("Send Email"):
           # Convert current page to PDF
           send_email(app, num_correct)


        for index, question in enumerate(app.questions):
            self.__render_question(question, app.get_answer(index))

        left, right = st.columns(2)

        with left:

            if st.button("Generate new exam"):
                app.reset()
                app.change_page(PageEnum.GENERATE_EXAM)

        with right:

            questions_to_pdf(app.questions, "questions.pdf")
            st.download_button(
                "Download",
                data=open("questions.pdf", "rb").read(),
                file_name="questions.pdf",
                mime="application/pdf",
                help="Download the questions as a PDF file"
            )

    def __render_question(self, question: Question, user_answer: int):
        """
        Render a question with the correct answer
        :param question: Question to render
        :param user_answer: Index of the answer selected by the user
        """
        st.write(f"**{question.id}. {question.question}**")

        if question.correct_answer == user_answer:
            for index, answer in enumerate(question.answers):
                if index == user_answer:
                    st.write(f":green[{chr(ord('a') + index)}) {answer}]")
                else:
                    st.write(f"{chr(ord('a') + index)}) {answer}")

        else:
            for index, answer in enumerate(question.answers):
                if index == user_answer:
                    st.write(f":red[{chr(ord('a') + index)}) {answer}]")
                elif index == question.correct_answer:
                    st.write(f":green[{chr(ord('a') + index)}) {answer}]")
                else:
                    st.write(f"{chr(ord('a') + index)}) {answer}")

        clarify_button = st.button(
            "Clarify the question",
            help="Get more information about the question",
            key=f"clarify_question_{question.id}"
        )

        if not clarify_button:
            return

        if question.id not in self.clarifications:
            st.warning("This can take a while...")
            self.clarifications[question.id] = clarify_question(question)

        st.write(self.clarifications[question.id])

    @staticmethod
    def __get_correct_answers(app):
        """
        Get the number of correct answers
        :param app: App instance
        :return: Number of correct answers
        """
        correct_answers = 0
        for index, question in enumerate(app.questions):
            if question.correct_answer == app.get_answer(index):
                correct_answers += 1

        return correct_answers

class QuestionBrowse:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.root_path = folder_path

    def browse_dir(self, app):
        files = os.listdir(self.folder_path)
        selected_item = st.selectbox("Select a file or folder:", files + ["Go Back"])
        if st.button("Go", key=f"{self.folder_path}_{selected_item}"):
           if selected_item == "Go Back":
               self.folder_path = self.root_path
               app.reset()
               app.change_page(PageEnum.GENERATE_EXAM)
           else:
               item_path = os.path.join(self.folder_path, selected_item)
               if os.path.isfile(item_path):
                   # Display file contents or perform actions
                   myq = MyQuestion()
                   app.questions = myq.read_json(app, item_path)
                   app.exam = item_path
                   app.change_page(PageEnum.QUESTIONS)
               elif os.path.isdir(item_path):
                   self.folder_path = item_path  # Update current folder
                   self.browse_dir(app)  # Recursively display files in the folder

    def render(self, app):
        st.title("Question Browser")
        self.browse_dir(app)

class EditJson:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def load_json_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    
    def save_json_file(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def rename_file(self,old_path, new_path):
        os.rename(old_path, new_path)

    def render(self, app):
        st.title("Edit Question Papers")

        files = os.listdir(self.folder_path)

        if st.button("Go Back"):
            app.reset()
            app.change_page(PageEnum.GENERATE_EXAM)

        files = [f for f in os.listdir(self.folder_path) if f.endswith('.json')]
        selected_file = st.selectbox("Select a Question file:", files)
    
        if selected_file:
            file_path = os.path.join(self.folder_path, selected_file)
            data = self.load_json_file(file_path)
    
            st.write("### JSON Content:")
            st.json(data)
    
            st.write("### Edit JSON Content:")
            edited_data = st.text_area("Edit JSON content:", value=json.dumps(data, indent=4), height=1000)
            new_file_name = st.text_input("Enter new file name (optional):")

            if st.button("Save"):
                try:
                    edited_data = json.loads(edited_data)
                    self.save_json_file(file_path, edited_data)
                    st.success("Question file saved successfully.")
                    if new_file_name and new_file_name != selected_file:
                        new_file_path = os.path.join(self.folder_path, new_file_name)
                        self.rename_file(file_path, new_file_path)
                        st.success("File renamed successfully.")

                except json.JSONDecodeError as e:
                    st.error("Invalid JSON format. Please correct the JSON content before saving.")



class MyQuestion:
    def __init__(self, id=None, question=None, answers=None, correct_answer=None):
        if id is not None:
           self.id = id
           self.question = question
           self.answers = answers
           self.correct_answer = correct_answer
    
    def setval(self, ques):
        self.id = ques.id
        self.question = ques.question
        self.answers = ques.answers
        self.correct_answer = ques.correct_answer
        return

    def to_dict(self,ques):
        self.setval(ques)
        return {
            'id': self.id,
            'question': self.question,
            'answers': self.answers,
            'correct_answer': self.correct_answer
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d['id'], d['question'], d['answers'], d['correct_answer'])

    # Convert JSON back to Python list
    def read_json(self, app, question_file):
        with open(question_file, "r", encoding="utf-8") as f:
        # Read the JSON data from the file
             json_data = f.read()        
        return [MyQuestion.from_dict(question) for question in json.loads(json_data)]

    def append_timestamp(self, filename):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name, extension = os.path.splitext(filename)
        return f"{base_name}_{timestamp}{extension}"

    def write_json(self, app, topics):
        json_data = json.dumps([self.to_dict(question) for question in app.questions], indent=4)
        with open(app.question_folder + os.sep + self.append_timestamp(self.sanitize_file_name(topics) + '.json'), "w", encoding="utf-8") as f:
                f.write(json_data)

    def sanitize_file_name(self,file_name):
        # Replace characters not allowed in file names with underscores
        sanitized_name = re.sub(r'[^\w.-]', '_', file_name)
        # Remove leading and trailing whitespaces
        sanitized_name = sanitized_name.strip()
        # Remove consecutive underscores
        sanitized_name = re.sub(r'_{2,}', '_', sanitized_name)
        # Remove leading periods or dashes
        sanitized_name = re.sub(r'^[-.]+', '', sanitized_name)
        # Remove trailing periods or dashes
        sanitized_name = re.sub(r'[-.]+$', '', sanitized_name)
        return sanitized_name[:100]

