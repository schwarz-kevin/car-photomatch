# Kurz-Anleitung: GitHub von v0.3.1 auf v0.4.12 aktualisieren

1. Die GitHub-Update-ZIP **entpacken**.
2. **Nicht** `git init` ausführen und **kein** neues GitHub-Repository erstellen.
3. In deinem bisherigen lokalen `car-photomatch`-Ordner Git Bash öffnen und prüfen:

   ```bash
   git status
   git pull --ff-only origin main
   ```

   Wenn `git status` nicht sauber ist, erst Änderungen sichern. Wenn du die README selbst geändert hast, die neue README entsprechend mit deinen Änderungen zusammenführen.
4. **Inhalt** des entpackten Update-Pakets über die Dateien des bestehenden lokalen `car-photomatch`-Ordners kopieren. Den versteckten `.git`-Ordner niemals löschen. Das Update-Paket enthält selbst keinen `.git`-Ordner.
5. Im bisherigen lokalen Repository:

   ```bash
   git add .
   git commit -m "Release Car PhotoMatch v0.4.12"
   git push origin main
   ```

6. Auf GitHub **Releases → Draft a new release** öffnen; Tag `v0.4.12`, Target `main`, Title `Car PhotoMatch v0.4.12`, **Pre-release** auswählen und die Datei `releases/car_photomatch_0_4_12_ui_workflow.zip` als Asset anhängen.

7. Verifizieren, dass README und Datei stimmen. Das alte Release v0.3.1 bleibt vorhanden.
