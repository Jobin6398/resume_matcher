from flask import Flask, request, render_template
from docx import Document
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import nltk
import spacy
from nltk.corpus import stopwords
from collections import Counter
import string
import os
from io import BytesIO
import base64
import fitz

nltk.download('stopwords')
nlp = spacy.load("en_core_web_sm")
stop_words = set(stopwords.words('english'))

app = Flask(__name__)

def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def read_docx(file):
    doc = Document(file)
    return " ".join([para.text for para in doc.paragraphs])

def read_file(file):
    filename = file.filename.lower()
    if filename.endswith(".docx"):
        return read_docx(file)
    elif filename.endswith(".pdf"):
        return read_pdf(file)
    else:
        return ""

def clean_text(text):
    words = text.lower().translate(str.maketrans('', '', string.punctuation)).split()
    return [word for word in words if word not in stop_words]

def extract_keywords_spacy(text):
    doc = nlp(text)
    keywords = set()
    for chunk in doc.noun_chunks:
        cleaned = chunk.text.lower().strip(string.punctuation)
        if cleaned not in stop_words and len(cleaned) > 1:
            keywords.add(cleaned)
    for ent in doc.ents:
        cleaned = ent.text.lower().strip(string.punctuation)
        if cleaned not in stop_words and len(cleaned) > 1:
            keywords.add(cleaned)
    return list(keywords)

def score_resume(resume_text, job_keywords_flat):
    resume_words = clean_text(resume_text)
    job_keywords_flat = list(dict.fromkeys(job_keywords_flat))
    matched = [word for word in job_keywords_flat if word in resume_words]
    missing = [word for word in job_keywords_flat if word not in resume_words]
    score = (len(matched) / len(job_keywords_flat)) * 100 if job_keywords_flat else 0
    return score, matched, missing

@app.route("/", methods=["GET", "POST"])
def index():
    result = {}
    if request.method == "POST":
        file = request.files.get("resume")
        job_description = request.form.get("job_description", "")
        if file and job_description:
            resume_text = read_file(file)
            job_keywords = extract_keywords_spacy(job_description)
            job_keywords_flat = list(dict.fromkeys([word for phrase in job_keywords for word in phrase.split() if word not in stop_words]))
            score, matched, missing = score_resume(resume_text, job_keywords_flat)
            result = {
                "score": f"{score:.2f}%",
                "matched": matched,
                "missing": missing,
            }
            if matched:
              # Join matched keywords into a single string
              wordcloud_text = " ".join(matched)
              # Generate the word cloud
              wc = WordCloud(width=800, height=400, background_color='white').generate(wordcloud_text)
              # Save to BytesIO stream instead of disk
              img = BytesIO()
              wc.to_image().save(img, format='PNG')
              img.seek(0)
              # Encode image to base64 to embed directly in HTML
              img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

              result['wordcloud_img'] = img_base64
    return render_template("index.html", result=result) 

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)