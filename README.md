# 🍽️ AI Kitchen

### Multimodal AI-Powered Recipe & Fridge Analysis System

AI Kitchen is an AI-powered application that uses **Generative AI + Computer Vision** to help users generate recipes and analyze ingredients from refrigerator images.

## 🚀 Features

- 🍽️ Generate recipes from dish or cuisine input  
- 🥬 Detect ingredients from fridge images  
- 🔍 Compare available vs required ingredients  
- 🛒 Identify missing ingredients  
- 🥗 Support dietary preferences  
- 💻 Interactive Gradio-based UI  

## 🧠 How It Works

1. User enters dish name or cuisine  
2. User uploads fridge image (optional)  
3. Vision model detects ingredients  
4. LLM generates recipe  
5. System compares ingredients  
6. Output shows:
   - Recipe
   - Available ingredients
   - Missing ingredients  

## 🏗️ Architecture

```
User Input → Gradio UI → Vision Model → LLM → Processing → Output
```

## 🛠️ Tech Stack

- **Language:** Python  
- **Platform:** Databricks  
- **UI:** Gradio (v3.50.2)  
- **Vision Model:** Llama 4 Maverick  
- **LLM:** Llama 3.3 70B Instruct  
- **Libraries:** OpenAI SDK, Databricks SDK, Pillow, Pandas  

## 🤖 Models Used

### Vision Model
- Detects ingredients from fridge images  

### Language Model
- Generates recipes  
- Processes ingredient comparison  

## 💡 Why This Project?

Instead of training custom ML models, this project uses **foundation models** to:

- Reduce development time  
- Improve scalability  
- Enable multimodal AI integration  

## ⚙️ Setup

```bash
pip install -r requirements.txt
```

## ☁️ Deployment

- Built and deployed on **Databricks Apps**
- Uses Databricks-hosted AI models

## 📸 Screenshots

### 🍽️ Recipe Generation
![Recipe]()

### 🥬 Fridge Analysis
![Fridge]()

### 🔍 Output Result
![Output]()

## 🎯 Project Background

Developed during a **6-month AI internship (IgnAite Technologies)**  
Focused on **GenAI, LLMs, and real-world deployment**

## 🗺️ Future Improvements

- 🔊 Voice assistant  
- 📜 Recipe history  
- 💾 Delta Lake storage  
- 📷 Real-time inventory detection  
- 🤖 Smart kitchen automation  

## 👩‍💻 Author

**Riya Yadav**  
AI/ML Engineer  

🔗 LinkedIn:  https://www.linkedin.com/in/riya-yadav31/

🔗 GitHub: https://github.com/riya-yadav31

## ⭐ If you like this project, give it a star!
