# GitHub publication checklist

No repository, push, publication, or release has been created for this delivery.

- [ ] Run the application and manual acceptance checklist using disposable notes.
- [ ] Review `VERIFICATION.md` and keep unverified platform/packaging claims accurate.
- [ ] Replace `[YEAR]` and `[COPYRIGHT HOLDER]` in `LICENSE` with your intended copyright details.
- [ ] Read `THIRD_PARTY_NOTICES.md`; retain dependency notices and separate dependency licenses. Do not label bundled Qt binaries as MIT.
- [ ] Run the automated suite on your publishing machine. Resolve acceptance issues before calling the beta accepted.
- [ ] Review all source/documentation and ensure no personal notes, session JSON, credentials, logs, virtual environment, test workspaces, or IDE files are included.
- [ ] Publish the **contents of `upt-beta`**, not its parent workspace. The parent contains local development/runtime and test artifacts.
- [ ] Check `.gitignore`; include original source, docs, sample notes, tests, dependency declarations, and license files.
- [ ] Create your own GitHub repository and choose its visibility. Initialize/commit/push only when you are ready.
- [ ] Describe it as **UPT 1.0 Beta / Python desktop Markdown editor**. Avoid full-platform or production-grade claims.
- [ ] If you attach binaries later, audit their exact Qt/third-party components, keep license/source/relinking requirements satisfied, and test installation on a clean machine. The supplied ZIP is source only.
- [ ] After acceptance fixes, implement future features yourself; use assistance for learning, design feedback, and review.
