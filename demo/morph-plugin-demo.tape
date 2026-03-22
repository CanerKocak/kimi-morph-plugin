Output morph-plugin-demo.mp4

Require bash
Require kimi
Require rg

Set Shell "zsh"
Set FontSize 20
Set Width 1500
Set Height 860
Set Padding 24
Set BorderRadius 18
Set Margin 24
Set MarginFill "#181926"
Set Theme "TokyoNightStorm"
Set WindowBar Colorful
Set Framerate 30
Set TypingSpeed 28ms

Sleep 1s

Hide
Type "bash ~/.kimi/plugins/morph-plugin/deactivate.sh 2>/dev/null || true"
Enter
Sleep 1s
Type "kimi plugin remove morph-plugin 2>/dev/null || true"
Enter
Sleep 1s
Show

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

Type "cd /tmp"
Enter
Sleep 500ms

Type "kimi"
Enter
Sleep 3s

Type "Remember for later: codename Night Glass; rejected migration TOML to YAML; safety phrase otters are not caches. Reply LOCKED only."
Enter
Sleep 7s

Type "What is the codename only?"
Enter
Sleep 6s

Type "/compact keep the codename, rejected migration, and safety phrase"
Enter
Sleep 4s

Type "What were the codename, migration, and safety phrase? One sentence."
Enter
Sleep 7s

Type "exit"
Enter
Sleep 1s
