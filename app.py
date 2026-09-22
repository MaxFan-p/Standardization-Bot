from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import config
import storage
from handlers import commands, events


def build_app():
    app = App(token=config.SLACK_BOT_TOKEN)
    commands.register(app)
    events.register(app)
    return app


def main():
    storage.init_db()
    import references_loader

    print("Loading reference specs (once, at startup)…")
    n = len(references_loader.load_reference_specs())
    print(f"{n} reference specs loaded.")
    app = build_app()
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    print("Privacy specs bot is running (Socket Mode). Ctrl-C to stop.")
    handler.start()


if __name__ == "__main__":
    main()