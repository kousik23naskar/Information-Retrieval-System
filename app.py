import streamlit as st
from src.helper import get_pdf_text, get_text_chunks, get_vector_store, get_tool_list, get_conversational_chain
from src.helper import arxiv, wiki


def display_chat_history(chat_history):
    for i, message in enumerate(chat_history):
        if i % 2 == 0:
            st.write("**User:** ", message.content)
        else:
            #st.write("Message object: ", message.__dict__)
            #source = message.metadata.get('source', 'Unknown source') if message.metadata else 'Unknown source'
            st.write("**Reply:** ", message.content)
            #st.write("Source: ", source)

def user_input():
    with st.form(key='user_question_form'):
        user_question = st.text_input("Ask a Question from the PDF Files", key="user_question_input")
        submit_button = st.form_submit_button(label='Generate')

    if submit_button and user_question:
        # Check if the conversation has been initialized
        if st.session_state.conversation is None:
            st.error("Please upload PDF documents and click 'Submit & Process' to initialize the conversation.")
            return

        # Send the question to the conversation agent and get the response
        response = st.session_state.conversation({'input': user_question})
        
        # Update the chat history in the session state with the new response
        st.session_state.chat_history = response['chat_history']
        
        # Display the updated chat history
        display_chat_history(st.session_state.chat_history)
        
        # Clear the user input box by setting the session state for 'user_question' to an empty string
        st.session_state.user_question = ""

        # Optionally, print sources if available
        # if 'source' in response:
        #     st.write("Source: ", response['source'])

def main():
    st.set_page_config(page_title="Information Retrieval")
    st.header("Information Retrieval System💁")
    
    if "conversation" not in st.session_state:
        # Initialize with arxiv and wiki tools if no conversation yet
        #st.session_state.conversation = get_conversational_chain([arxiv, wiki])
        st.session_state.conversation = None
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Add a reset button
    if st.button("Reset Conversation"):
        st.session_state.chat_history = []
        st.session_state.conversation = None
        st.success("Conversation has been reset.")

    user_input()

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader(
            "Upload your PDF Files and Click on the Submit & Process Button", 
            accept_multiple_files=True
        )
        if st.button("Submit & Process"):
            if not pdf_docs:
                st.error("No PDF documents uploaded. Please upload at least one PDF file.")
            else:
                with st.spinner("Processing..."):
                    raw_text = get_pdf_text(pdf_docs)
                    text_chunks = get_text_chunks(raw_text)

                    if text_chunks:
                        pdf_tool = get_vector_store(text_chunks)
                        tool_list = get_tool_list(pdf_tool)
                    else:
                        # If no text chunks, fallback to arxiv and wiki
                        tool_list = [arxiv, wiki]
                    
                    # Update the conversation with the new tool list
                    st.session_state.conversation = get_conversational_chain(tool_list)
                    st.success("Done")


    # Footer
    st.markdown("""
    <style>
    .developer-label {
        position: fixed;
        bottom: 0;
        width: calc(100% - var(--sidebar-width, 0px)); /* Adjust width based on sidebar */
        text-align: center;
        background-color: #f0f0f0;
        padding: 10px;
        border-top: 1px solid #ddd;
        left: var(--sidebar-width, 0px); /* Adjust position based on sidebar */
    }
    </style>
    <div class="developer-label">
        <p>Developed by Kousik Naskar | Email: <a href="mailto:kousik23naskar@gmail.com">kousik23naskar@gmail.com</a></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
