Run the knowledge pipeline on a URL or text.
Read the URL/text from Ahmed, then:
1. Use fetch_content() from claude-pipeline to scrape
2. Triage with triage()
3. Write insight with write_insight()
4. Index to ChromaDB with index_insight()
5. Notify Ahmed via riri-notify.sh
Location: ~/projects/riri/pipeline_intake.py
