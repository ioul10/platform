name: 📊 Update Market Data

on:
  schedule:
    # Toutes les 4 heures pendant les jours ouvres (Lun-Ven)
    # 09:35 UTC+1 = 08:35 UTC (ouverture)
    # 12:00 UTC+1 = 11:00 UTC (mi-seance)
    # 15:35 UTC+1 = 14:35 UTC (cloture)
    - cron: '35 8,11,14 * * 1-5'
  workflow_dispatch: # Permet le declenchement manuel

jobs:
  update-data:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Clear cache and scrape fresh data
        run: |
          python -c "
          from scraper import (
              clear_cache, scrape_masi_index, scrape_top_movers, 
              scrape_futures_data, _save_history
          )
          
          print('=== Clearing cache ===')
          clear_cache()
          
          print('=== Scraping MASI ===')
          masi = scrape_masi_index(force_refresh=True)
          print(f'  MASI: {masi.get(\"masi\")}')
          print(f'  MASI 20: {masi.get(\"masi20\")}')
          
          print('=== Scraping top movers ===')
          movers = scrape_top_movers(force_refresh=True)
          print(f'  Gainers: {len(movers[\"gainers\"])}')
          print(f'  Losers: {len(movers[\"losers\"])}')
          
          print('=== Scraping futures ===')
          futures = scrape_futures_data(force_refresh=True)
          _save_history(futures)
          total_vol = sum(c.get('volume_mad', 0) for c in futures.values())
          total_ct = sum(c.get('nb_contrats', 0) for c in futures.values())
          print(f'  Total: {total_vol:,.0f} MAD / {total_ct} contrats')
          
          print('=== Done ===')
          "
      
      - name: Commit and push
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "📊 Auto-update market data"
          file_pattern: "data/*.json data/cache/*.json"
