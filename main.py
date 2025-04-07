import os
import json
from datetime import datetime
#import pandas as pd
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils import constants
from utils.db_utils import fetch_from_db_interview

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI clients (Python 3.12 compatible syntax)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Establish db connection
conn = psycopg2.connect(**constants.connection_params)
cursor = conn.cursor()

# Check and create the output directory if it doesn't exist
if not os.path.exists("output"):
    os.makedirs("output")

# Evaluation Functions
def format_interview_conversation(transcript: str) -> str:
    instructs = '''The following is an example of how the conversation has to be formatted:

**Interviewer:** Hi Venkatesh Pattepur, welcome to the interview for the position of Lead DevOps Engineer. During this interview, I will ask a total of 8 to 10 questions, with follow-ups where necessary to dive deeper into your responses. After I finish asking a question, you can begin answering. Let's begin. How are you today?

**Candidate:** Yeah, I'm fine. What about you? Can you hear me right? Hello? Hello?

**Interviewer:** Thank you for your response. Let's stay focused on the interview questions. Can you describe your experience with deploying and managing infrastructure on Azure? Please provide examples of Azure services you have utilized and how you optimize their performance and cost.

**Candidate:** Yeah, in Azure for deploying, we are using infrastructure as code tool like Terraform. We have created Terraform modules for various clouds, mainly focusing on Azure. I have written over 60 sets of Terraform scripts. With these modules, we can easily deploy applications and scale them up or down. For cost optimization, we can reserve instances for different periods based on usage, and also utilize Azure Advisor for recommendations on security, reliability, and efficiency to improve cost management.

**Interviewer:** Thank you for sharing your experience. I'd like to ask a few follow-up questions for clarity. One, you mentioned using Terraform for deploying infrastructure. Can you elaborate on a specific module you created and the challenges you faced during its implementation? Two, you also spoke about Azure Advisor. Can you provide an example of a recommendation from Azure Advisor that you implemented and how it impacted your costs or performance?
'''
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that formats interview transcripts into clear conversations. " + instructs},
                {"role": "user", "content": f"Convert the following interview transcript into a proper conversation between interviewer and candidate efficiently. Maintain the original content but format it with clear speaker labels and proper formatting. Fix any grammatical issues efficiently while keeping the original meaning:\n\n{transcript}"}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise ValueError(f"Failed to format conversation: {str(e)}")

def evaluate_conversation(conversation: str) -> str:
    evaluation_prompt = '''You are an assistant that extracts structured evaluation information of a candidate from a conversation between Interviewer and Candidate
**Evaluate the candidate's response based on the question asked, considering the following key parameters:**  

### **1) Project Experience**  
- Does the candidate demonstrate hands-on experience with relevant projects?  
- Are specific details, methodologies, tools, or technologies mentioned?  
- Does the response include concrete examples to illustrate past contributions and achievements?  

### **2) Client Communication & Stakeholder Management**  
- How effectively does the candidate describe their ability to engage with clients, brokers, or developers?  
- Are specific strategies, challenges faced, or successful interactions highlighted?  
- Does the candidate demonstrate strong interpersonal skills and the ability to manage expectations?  

### **3) Motivation & Career Vision**  
- Does the candidate clearly articulate their motivation for the role and industry?  
- Is their response aligned with long-term professional growth and aspirations?  
- Do they exhibit enthusiasm, passion, or a well-defined career trajectory?  

### **4) Role Alignment & Adaptability**  
- Does the candidate’s response align with the job responsibilities and expectations?  
- Do they demonstrate a willingness to adapt to the role’s demands and evolving industry trends?  
- Are they open to learning new skills or taking on additional responsibilities?  

### **5) Technical Proficiency**  
- Does the candidate showcase relevant technical knowledge, tools, or frameworks?  
- Are their responses accurate, well-structured, and relevant to the industry?  
- Do they demonstrate problem-solving skills through technical examples or case studies?  

### **6) Problem-Solving & Analytical Thinking**  
- Does the candidate exhibit strong critical thinking and decision-making abilities?  
- Are specific problem-solving approaches, methodologies, or frameworks discussed?  
- Do they illustrate resilience and adaptability in tackling challenges?  

### **7) Creativity, Innovation & Strategic Thinking**  
- Does the candidate demonstrate an innovative mindset or unique problem-solving strategies?  
- Are fresh perspectives, unconventional solutions, or process improvements mentioned?  
- Do they show the ability to think beyond conventional approaches?  

### **General Evaluation Considerations:**  
- Is the response well-articulated, structured, and engaging?  
- Does the candidate provide specific examples rather than generic statements?  
- How effectively do they communicate their thoughts, ensuring clarity and relevance?  

_Assess the candidate’s answer holistically, considering both depth of knowledge and ability to convey ideas effectively._ 

# Scoring Guidelines:

-1: **Absolutely Out of Context**
-- The answer is entirely unrelated to the question, irrelevant, or nonsensical.
-- It provides no value or connection to the topic or role requirements.

0: **Completely Irrelevant or Incomprehensible**
-- The answer is off-topic, unintelligible, or fails to address the question in any way.
-- No meaningful information or relevance is provided.

1: **Minimally Relevant but Poor Quality**
-- The answer is slightly related to the question but lacks clarity, coherence, or meaningful content.
-- It does not address the question effectively or provide useful insights.

2: **Partially Relevant but Superficial**
-- The answer touches on the topic but lacks depth, specificity, or alignment with the role.
-- It provides minimal value and fails to address the question adequately.

3: **Somewhat Relevant but Limited**
-- The answer addresses the question partially but lacks depth, examples, or strong alignment with the role.
-- It provides some value but is incomplete or underdeveloped.

4: **Moderately Relevant and Adequate**
-- The answer addresses the question sufficiently but lacks strong depth, clarity, or examples.
-- It demonstrates basic alignment with the role but could be more detailed or insightful.

5: **Relevant and Clear**
-- The answer is relevant, clear, and addresses the question adequately.
-- It provides a reasonable level of depth and alignment with the role but could benefit from more specificity or examples.


Evaluate the conversation **STRICTLY** according to all the evaluation metrics defined above and return the scores and genuine reasonings in a well-structured manner.
The Reasoning MUST explain the **lack** in the answer which makes the candidate realize his state for scoring a perfect 5.

INTERVIEW CONVERSATION:

{conversation}

'''
    user_prompt = '''### **Comprehensive Candidate Evaluation & Scoring**  

Evaluate the conversation **STRICTLY** according to all the evaluation metrics defined above and return the scores in a well-structured manner. 

#### **Segregated Score Reporting:**  

1) **Non-Technical**  
   - This section should contain the parameters focusing on skills such as behavioral traits, communication, professionalism, and overall fit for the role.  
   - Evaluate and average the scores of these parameters and display it as the final **Non-Technical** score.  

2) **Subject Matter Expertise**  
   - This section should include skillset-based scores that are closely aligned with the technical requirements and core competencies of the job profile.  
   - Evaluate and average these scores and display it as the final **Subject Matter Expertise** score.  

#### **Final Report Presentation:**  

- Display both scores prominently, one above the other.  
- Provide a **detailed reasoning** for the assigned scores. This should summarize the strengths and weaknesses of the candidate across all evaluated parameters.  
- Include **specific insights** that highlight key strengths and areas for improvement.  
- Ensure the feedback is constructive, precise, and aligns with the job expectations.  


Follow the below template to generate the final evaluation report:

### **Evaluation Report Format:**  

#### **Subject Matter Expertise:**  
- **Project Experience:**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

- **Role Fit:**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

- **Technical Proficiency:**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

- **Client Communication (Only for Business-Oriented Roles):**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

#### **Non-Technical Expertise:**  
- **Client Communication (Only for Technical Roles):**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

- **Motivation:**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

- **Problem-Solving:**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

- **Creativity & Innovation:**  
  - Score: _[Insert Score]_  
  - Reasoning: _[Insert Explanation]_  

#### **Final Scores:**  
- **Subject Matter Expertise Average Score:** _[Calculated Average]_  
- **Non-Technical Average Score:** _[Calculated Average]_  

#### **Summary:**  
_Provide a well-rounded summary of the candidate’s strengths, weaknesses, and overall suitability for the role. Highlight key insights from each category and offer constructive feedback. Make sure to start the summary with candidate's first name._  
'''
    try:
        evaluation_prompt = evaluation_prompt.format(conversation=conversation)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": evaluation_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise ValueError(f"Failed to evaluate conversation: {str(e)}")

def parse_evaluation_report(eval_report: str) -> dict:
    logger.info("Parsing evaluation report")
    system_prompt = '''You are an assistant that extracts structured information from evaluation reports.
Extract the following information from the evaluation report text below:

1. **Candidate Name**
2. **Subject Matter Expertise** (Scores and Reasoning for Project Experience, Role Fit, and Technical Proficiency)
3. **Non-Technical Expertise** (Scores and Reasoning for Client Communication, Motivation, Problem-Solving, and Creativity & Innovation)
4. **Final Scores** (Subject Matter Expertise Average Score, Non-Technical Average Score)
5. **Summary**

Please provide the extracted information in JSON format as shown below:

{{
    "Candidate Name": "",
    "Subject Matter Expertise": {{
        "Project Experience": {{"Score": "", "Reasoning": ""}},
        "Role Fit": {{"Score": "", "Reasoning": ""}},
        "Technical Proficiency": {{"Score": "", "Reasoning": ""}}
    }},
    "Non-Technical Expertise": {{
        "Client Communication": {{"Score": "", "Reasoning": ""}},
        "Motivation": {{"Score": "", "Reasoning": ""}},
        "Problem-Solving": {{"Score": "", "Reasoning": ""}},
        "Creativity & Innovation": {{"Score": "", "Reasoning": ""}}
    }},
    "Final Scores": {{
        "Subject Matter Expertise Average Score": "",
        "Non-Technical Average Score": ""
    }},
    "Summary": ""
}}
'''
    user_prompt = f"**Evaluation Report Text:**\n\n#############\n\n{eval_report}\n\n#############"
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    extracted_info = response.choices[0].message.content.strip()
    json_start = extracted_info.find('{')
    json_end = extracted_info.rfind('}') + 1
    result = json.loads(extracted_info[json_start:json_end])
    logger.info(f"Parsed evaluation report: {json.dumps(result, indent=2)}")
    return result

def flatten_evaluation_data(eval_data: dict, email: str, job_id: str) -> list:
    logger.info("Flattening evaluation data")
    records = []
    updated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Subject Matter Expertise
    for subcat, details in eval_data["Subject Matter Expertise"].items():
        try:
            score = int(round(float(details["Score"])))  # Round to nearest integer
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid score for {subcat}: {details.get('Score', 'None')}, setting to 0. Error: {str(e)}")
            score = 0
        records.append({
            "email": email,
            "job_id": job_id,
            "category": "Subject Matter Expertise",
            "subcategory": subcat,
            "reasoning": details.get("Reasoning", ""),
            "score": score,
            "updated_time": updated_time
        })
    
    # Non-Technical Expertise
    for subcat, details in eval_data["Non-Technical Expertise"].items():
        try:
            score = int(round(float(details["Score"])))  # Round to nearest integer
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid score for {subcat}: {details.get('Score', 'None')}, setting to 0. Error: {str(e)}")
            score = 0
        records.append({
            "email": email,
            "job_id": job_id,
            "category": "Non-Technical Expertise",
            "subcategory": subcat,
            "reasoning": details.get("Reasoning", ""),
            "score": score,
            "updated_time": updated_time
        })
    
    # Final Scores
    for category, score_key in [("Subject Matter Expertise", "Subject Matter Expertise Average Score"),
                              ("Non-Technical Expertise", "Non-Technical Average Score")]:
        try:
            score = int(round(float(eval_data["Final Scores"][score_key])))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid average score for {score_key}: {eval_data['Final Scores'].get(score_key, 'None')}, setting to 0. Error: {str(e)}")
            score = 0
        records.append({
            "email": email,
            "job_id": job_id,
            "category": category,
            "subcategory": "Average",
            "reasoning": "Average score based on subcategory evaluations",
            "score": score,
            "updated_time": updated_time
        })
    
    logger.info(f"Flattened records: {json.dumps(records, indent=2)}")
    return records

def add_evaluation_to_db(records: list) -> str:
    logger.info("Adding evaluation data to database")
    connection_params = {
        'dbname': 'postgres',
        'user': 'postgres',
        'password': 'analytics123',
        'host': '34.132.249.54',
        'port': '5432'
    }
    try:
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor()
        
        MIN_SCORE = 0
        MAX_SCORE = 10  # Adjust based on your actual constraint
        
        insert_query = """
        INSERT INTO EvaluationScores (email, job_id, category, subcategory, reasoning, score, updated_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
        """
        
        successful_inserts = 0
        for record in records:
            # Validate and clamp score
            score = max(MIN_SCORE, min(MAX_SCORE, record["score"]))
            try:
                cursor.execute(insert_query, (
                    record["email"],
                    record["job_id"],
                    record["category"],
                    record["subcategory"],
                    record["reasoning"],
                    score,
                    record["updated_time"]
                ))
                successful_inserts += 1
            except psycopg2.Error as e:
                logger.error(f"Database error for record {record}: {str(e)}")
                conn.rollback()
                raise
        
        conn.commit()
        db_message = f"Data inserted successfully into the database! ({successful_inserts}/{len(records)} rows)"
        logger.info(db_message)
        
    except psycopg2.Error as e:
        db_message = f"Database error: {str(e)}"
        logger.error(db_message)
        raise
    except Exception as e:
        db_message = f"Unexpected error: {str(e)}"
        logger.error(db_message)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return db_message

# Flask Endpoints
@app.route('/evaluate', methods=['POST'])
def evaluate_response():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        job_id = data.get('job_post_id')
        logger.info(f"Received request: user_id={user_id}, job_id={job_id}")
        interview_data = fetch_from_db_interview(conn, cursor, user_id, job_id)
        if not interview_data or len(interview_data) != 8:
            return jsonify({"error": "No valid interview data found for the given user_id and job_id."}), 404
        email = interview_data[2]
        transcript = interview_data[6]

        if not email or not job_id or not transcript:
            return jsonify({"error": "Fields 'email', 'job_id', and 'sampleanswer' are required."}), 400

        if not transcript:
            return jsonify({"error": "No transcript available for evaluation."}), 400

        # Evaluate the transcript
        conversation = format_interview_conversation(transcript)
        logger.info("Formatted conversation")
        eval_report = evaluate_conversation(conversation)
        logger.info("Evaluated conversation")
        eval_data = parse_evaluation_report(eval_report)

        records = flatten_evaluation_data(eval_data, email, job_id)
        db_message = add_evaluation_to_db(records)

        # Return response with additional fetched data
        return jsonify({
            "email": email,
            "job_id": job_id,
            "user_id": user_id,
            #"user_name": user_name,
            #"job_title": job_title,
            #"job_description": job_description,
            #"interview_created_at": str(interview_created_at),
            "transcript": transcript,  # Include transcript for verification
            "evaluation_scores": eval_data,
            "overall_score": {
                "Subject Matter Expertise": eval_data["Final Scores"]["Subject Matter Expertise Average Score"],
                "Non-Technical": eval_data["Final Scores"]["Non-Technical Average Score"]
            },
            "db_message": db_message,
            "message": "Evaluation completed successfully and data stored in the database."
        }), 200

    except Exception as e:
        logger.error(f"Exception in evaluate_response: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)