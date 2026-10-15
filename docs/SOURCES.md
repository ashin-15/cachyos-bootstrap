# Installer provenance

- [OpenAI documentation: current Codex npm installation](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)
- [Claude Code installation](https://support.claude.com/en/articles/14552382-your-first-day-in-claude-code)
- [Antigravity CLI](https://github.com/google-antigravity/antigravity-cli)
- [Kiro downloads](https://kiro.dev/downloads/)
- [no-mistakes installer](https://github.com/kunchenguid/no-mistakes)
- [Hermes source](https://github.com/NousResearch/hermes-agent)
- [camp-fi source](https://github.com/ashin-15/camp-fi)
- [Android SDK tooling and licenses](https://developer.android.com/tools/agents/android-cli/commands/sdk_install)
- [LM Studio CLI setup](https://github.com/lmstudio-ai/lms)

Vendor installers are fetched over HTTPS, saved to a temporary file, and displayed for review
before execution unless explicitly opted out. Their observed checksums are printed for that
execution; an observed checksum alone is not an independent authenticity guarantee.

The Android CLI seed is checksummed in the private overlay and updated through Google's
`android update` command before SDK installation. The stable SDK component identifiers are
resolved against Google's repository catalog, and `android sdk install` fetches them.
The deprecated SDK manager is not invoked by this bootstrap.
