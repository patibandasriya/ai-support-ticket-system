import os

import requests
import streamlit as st


# --------------------------------------------------
# Backend URL
# --------------------------------------------------

API_URL = os.getenv("API_URL", "http://127.0.0.1:8004")


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="AI Support Ticket Analyst",
    page_icon="🎫",
    layout="wide",
)


# --------------------------------------------------
# Page design
# --------------------------------------------------

st.title("🎫 AI Support Ticket Analyst")

st.caption(
    "Ask natural-language questions about support tickets "
    "and inspect unusual ticket patterns."
)

st.divider()


# --------------------------------------------------
# Backend health check
# --------------------------------------------------

try:
    health_response = requests.get(
        f"{API_URL}/health",
        timeout=10
    )

    if health_response.status_code == 200:
        health_data = health_response.json()

        st.success(
            f"Backend connected successfully. "
            f"{health_data.get('rows_loaded', 0)} tickets loaded."
        )
    else:
        st.warning("Backend is running but returned an error.")

except requests.exceptions.RequestException:
    st.error(
        "Backend is not connected. "
        "Please start the FastAPI server first."
    )


# --------------------------------------------------
# Ask question
# --------------------------------------------------

st.subheader("Ask a question")

question = st.text_input(
    "Enter your question",
    value="How many tickets are currently open?",
)


if st.button("Ask", type="primary"):

    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            response = requests.post(
                f"{API_URL}/query",
                json={
                    "question": question
                },
                timeout=30,
            )

            if response.status_code != 200:
                st.error(
                    f"Backend error: {response.text}"
                )
            else:
                result = response.json()

                st.subheader("Answer")

                query_result = result.get("result", {})

                operation = query_result.get("operation")

                if operation == "count":
                    st.metric(
                        "Ticket Count",
                        query_result.get("count", 0)
                    )

                elif operation == "average":
                    st.metric(
                        "Average Resolution Time",
                        query_result.get("average", 0)
                    )

                    st.write(
                        f"Column used: "
                        f"{query_result.get('column', 'Not available')}"
                    )

                elif operation == "group":
                    groups = query_result.get("groups", [])

                    if groups:
                        st.dataframe(
                            groups,
                            use_container_width=True
                        )
                    else:
                        st.info(
                            query_result.get(
                                "message",
                                "No grouped results found."
                            )
                        )

                elif operation == "list":
                    ticket_rows = query_result.get(
                        "tickets",
                        []
                    )

                    st.write(
                        f"Total matching tickets: "
                        f"{query_result.get('count', 0)}"
                    )

                    st.dataframe(
                        ticket_rows,
                        use_container_width=True
                    )

                else:
                    st.json(result)

                with st.expander("Technical details"):
                    st.json(result)

        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to the backend. "
                "Make sure FastAPI is running on port 8000."
            )

        except requests.exceptions.Timeout:
            st.error(
                "The backend took too long to respond."
            )

        except Exception as error:
            st.error(
                f"Unexpected error: {error}"
            )


# --------------------------------------------------
# Anomalies
# --------------------------------------------------

st.divider()

st.subheader("🚨 Ticket Anomalies")

if st.button("Inspect Anomalies"):

    try:
        response = requests.get(
            f"{API_URL}/anomalies",
            timeout=30
        )

        if response.status_code != 200:
            st.error(
                f"Backend error: {response.text}"
            )
        else:
            anomaly_data = response.json()

            total_anomalies = anomaly_data.get(
                "total_anomalies",
                0
            )

            st.metric(
                "Anomaly Types Found",
                total_anomalies
            )

            anomaly_list = anomaly_data.get(
                "anomalies",
                []
            )

            if not anomaly_list:
                st.success(
                    "No anomalies were detected."
                )
            else:
                for anomaly in anomaly_list:
                    st.warning(
                        anomaly.get(
                            "description",
                            "Anomaly detected."
                        )
                    )

                    st.write(
                        f"Count: {anomaly.get('count', 0)}"
                    )

                    if anomaly.get("tickets"):
                        st.dataframe(
                            anomaly["tickets"],
                            use_container_width=True
                        )

    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the backend. "
            "Make sure FastAPI is running on port 8000."
        )

    except Exception as error:
        st.error(
            f"Unexpected error: {error}"
        )