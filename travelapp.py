import streamlit as st
import json
import requests
import markdown
import logging
from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# ----------------- Load and Save Users -----------------
USER_FILE = "users.json"

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"users": []}

def save_users(users_data):
    with open(USER_FILE, "w") as file:
        json.dump(users_data, file, indent=4)

# ----------------- User Authentication -----------------
def verify_user(username, email, mobile):
    users = load_users()["users"]
    for user in users:
        if user["username"] == username and user["email"] == email and user["mobile"] == mobile:
            return True
    return False

def register_user(username, email, mobile):
    users_data = load_users()
    for user in users_data["users"]:
        if user["username"] == username:
            return False, "⚠️ Username already exists. Please use a different one."
    users_data["users"].append({"username": username, "email": email, "mobile": mobile})
    save_users(users_data)
    return True, "✅ Registration successful! You can now log in."

# ----------------- Initialize AI Model -----------------
class PlannerState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]
    city: str
    interests: List[str]
    itinerary: str

llm = ChatGroq(
    temperature=0.7,
    groq_api_key="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",
    model_name="llama-3.3-70b-versatile"
)

logging.basicConfig(
    filename="system_interaction.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_interaction(user_input, response):
    logging.info(f"User Input: {user_input} | Response: {response}")

# ----------------- Travel Planning Functions -----------------
def input_city(city: str, state: PlannerState) -> PlannerState:
    return {
        **state,
        "city": city,
        "messages": state["messages"] + [HumanMessage(content=f"City: {city}")]
    }

def input_interests(interests: str, state: PlannerState) -> PlannerState:
    interest_list = [interest.strip() for interest in interests.split(",")]
    return {
        **state,
        "interests": interest_list,
        "messages": state["messages"] + [HumanMessage(content=f"Interests: {', '.join(interest_list)}")]
    }

def create_itinerary(state: PlannerState) -> str:
    itinerary_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a smart travel agent who creates engaging, fun, and optimized day trip itineraries for {city}. \
        Tailor recommendations based on the user's interests: {interests}. \
        Include hidden gems, famous spots, and local cuisine. Keep it structured, with timestamps."),
        ("human", "Plan my perfect day trip!")
    ])

    response = llm.invoke(itinerary_prompt.format_messages(city=state["city"], interests=', '.join(state["interests"])))
    itinerary_markdown = response.content
    return markdown.markdown(itinerary_markdown)

def get_weather(city: str) -> str:
    api_key = "b787841c42e84b32b70235141251102"
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}&aqi=no"
    try:
        response = requests.get(url)
        data = response.json()
        if "current" in data:
            weather_desc = data["current"]["condition"]["text"]
            temp = data["current"]["temp_c"]
            return f"🌤 **Current weather in {city}:** {weather_desc}, {temp}°C"
        else:
            return "⚠️ Weather data unavailable."
    except:
        return "❌ Error fetching weather."

def fun_fact(city: str) -> str:
    fun_fact_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a knowledgeable travel guide. Share an interesting and unique fun fact about {city} that most travelers don’t know."),
        ("human", "Tell me a fun fact about {city}!")
    ])

    response = llm.invoke(fun_fact_prompt.format_messages(city=city))
    return f"🎉 **Fun Fact:** {response.content}"

# ----------------- Streamlit UI -----------------
st.title("✈️ AI Travel Planner")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --------- LOGIN / REGISTER PAGE ---------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

    with tab1:
        st.subheader("User Login")
        username = st.text_input("Username", key="login_username")
        email = st.text_input("Email", key="login_email")
        mobile = st.text_input("Mobile Number", key="login_mobile")
        if st.button("Login"):
            if verify_user(username, email, mobile):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"✅ Welcome {username}! Redirecting to AI Travel Planner...")
                st.rerun()
            else:
                st.error("❌ Invalid credentials. Please try again.")

    with tab2:
        st.subheader("User Registration")
        reg_username = st.text_input("Choose a Username", key="reg_username")
        reg_email = st.text_input("Email Address", key="reg_email")
        reg_mobile = st.text_input("Mobile Number", key="reg_mobile")
        if st.button("Register"):
            success, message = register_user(reg_username, reg_email, reg_mobile)
            if success:
                st.success(message)
            else:
                st.error(message)

# --------- TRAVEL PLANNER PAGE ---------
else:
    st.sidebar.subheader(f"👤 Logged in as: {st.session_state.username}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    st.subheader("🌍 Plan Your Next Trip!")
    
    city = st.text_input("Enter the city for your trip", placeholder="e.g., Ahmedabad", key="trip_city")
    interests = st.text_input("Enter your interests (comma-separated)", placeholder="e.g., Food, Culture, Adventure", key="trip_interests")

    if st.button("Generate Itinerary"):
        state = {"messages": [], "city": "", "interests": [], "itinerary": ""}
        state = input_city(city, state)
        state = input_interests(interests, state)

        itinerary = create_itinerary(state)
        weather = get_weather(city)
        fact = fun_fact(city)

        log_interaction(f"City: {city}, Interests: {interests}", f"Itinerary: {itinerary}, Weather: {weather}, Fun Fact: {fact}")

        st.markdown(itinerary, unsafe_allow_html=True)
        st.write(weather)
        st.write(fact)
