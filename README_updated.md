
# svApp

![Logo](image.png)

**Description:**  
Lizi app server.

## Structure
- app/main.py: main script including all FastAPI endpoints
- app/utils/api_funcs_ss5.py: RadioManager service. Performs all logic on network API. Acts as a middle-man between client and network
- app/utils/send_commands.py: Messages service. In charge of communication with network API, credentials, and HTTP session management.

## Issues and Bug Reports
If you encounter any issues, please report them under the Issues tab, and we'll fix them within 5-10 seconds (approximately).

## Installation

To set up the project locally, follow these steps:

1. **Clone the repository:**

   ```bash
   git clone https://github.com/levph/svApp.git
   cd svApp
   ```

2. **Create and activate a virtual environment (optional but recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the required dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Usage

## IT'S INTUITIVE YOU GOT IT, I BELIEVE IN YOU!

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature/YourFeatureName`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/YourFeatureName`
5. Open a pull request.

Please ensure your code adheres to the project's coding standards and includes appropriate tests.
