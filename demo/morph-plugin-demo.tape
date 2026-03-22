Output morph-plugin-demo.mp4

Require bash
Require kimi
Require rg

Set Shell "zsh"
Set FontSize 18
Set Width 1720
Set Height 980
Set Padding 28
Set BorderRadius 22
Set Margin 28
Set MarginFill "#0b1020"
Set Theme "TokyoNightStorm"
Set WindowBar Colorful
Set WindowBarSize 48
Set Framerate 30
Set TypingSpeed 24ms

Sleep 1s

Type "kimi plugin install git@github.com:CanerKocak/kimi-morph-plugin.git"
Enter
Sleep 3s

Type "bash ~/.kimi/plugins/morph-plugin/activate.sh"
Enter
Sleep 2s

Type "kimi plugin list"
Enter
Sleep 2s

Type "kimi plugin info morph-plugin"
Enter
Sleep 2s

Type "rg compaction_plugin ~/.kimi/config.toml"
Enter
Sleep 2s

Type "cd /Users/caner/kimi-morph-plugin"
Enter
Sleep 500ms

Type "kimi --no-thinking"
Enter
Sleep 3s

Type "Read only. Which file declares the plugin entrypoint, and what is it? One line."
Enter
Sleep 5s

Type "Read only. Which config key does activate.py write? One line."
Enter
Sleep 5s

Type "Read only. Which exact line does deactivate.py remove? One line."
Enter
Sleep 5s

Type "Read only. How is the compact URL built? One line."
Enter
Sleep 6s

Type "Read only. Which request headers are added? One line."
Enter
Sleep 5s

Type "Read only. Which error type is raised when Kimi provider creds are missing? One line."
Enter
Sleep 5s

Type "/compact keep the entrypoint, key, removed line, compact URL rule, headers, and missing-creds error."
Enter
Sleep 4s

Type "After compaction, list those six facts in six bullets."
Enter
Sleep 10s

Type "exit"
Enter
Sleep 1s
