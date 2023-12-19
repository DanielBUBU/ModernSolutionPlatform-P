import os
from streamlit.web import bootstrap

#https://discuss.streamlit.io/t/using-pyinstaller-or-similar-to-create-an-executable/902/84

def main():
    os.chdir(os.path.dirname(__file__))

    flag_options = {
        "server.port": 8051,
        "global.developmentMode": False,
    }

    bootstrap.load_config_options(flag_options=flag_options)
    flag_options["_is_running_with_streamlit"] = True
    bootstrap.run(
        "./frontend.py",
        "streamlit run",
        [],
        flag_options,
    )

if __name__ == "__main__":
    main()