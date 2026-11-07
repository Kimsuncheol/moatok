# Agent Instructions

The agent must redeploy this project to Firebase hosting whenever the frontend or backend changes.
The agent must also automatically commit and push the changes to the repository.

# Frontend
- Every font weight, font size, and font color must be in each global file.
- If each global file is changed, the agent must update the changes in the other global files.
- If each global file doesn't exist, the agent must create it.
- webkit scrollbar is allowed, but the scroll bar must be hidden in the mobile environment. 
- Build all time and timer pickers using a shared, reusable time-picker component with styles defined in the global stylesheet(s).
- When the user requests a time-picker design change, apply the change consistently to every time and timer picker throughout the application, including existing pickers. Do not maintain separate designs or duplicated picker implementations.


