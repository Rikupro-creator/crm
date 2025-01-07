# Save this code in a file named `app.py`
import streamlit as st

# App title
st.title("Streamlit Deployment Test")

# Display a simple message
st.write("Hello, Streamlit!")

# Add an input box and button
user_input = st.text_input("Enter something:", "")
if st.button("Submit"):
    st.write(f"You entered: {user_input}")

# Display an interactive chart
import pandas as pd
import numpy as np

# Generate some data
data = pd.DataFrame(
    np.random.randn(10, 2),
    columns=['X', 'Y']
)

st.line_chart(data)
