"""
Billboard chart scraper for nostalgia recommendations
"""

import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.models import BillboardChart
from app.services.spotify_client import SpotifyClient

logger = logging.getLogger(__name__)


class BillboardScraper:
    """Service for scraping Billboard chart data"""

    def __init__(self):
        self.base_url = "https://www.billboard.com/charts/hot-100"
        self.spotify_client = SpotifyClient()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def scrape_years(self, years: List[int], db: Session, access_token: str = None):
        """Scrape Billboard Hot 100 data for specified years"""
        try:
            for year in years:
                logger.info(f"Scraping Billboard data for year {year}")
                self._scrape_year(year, db, access_token)
                time.sleep(2)  # Be respectful to Billboard's servers

        except Exception as e:
            logger.error(f"Failed to scrape Billboard data: {e}")

    def _scrape_year(self, year: int, db: Session, access_token: str = None):
        """Scrape Billboard Hot 100 data for a specific year"""
        # Sample key dates throughout the year (quarterly)
        sample_dates = [
            datetime(year, 3, 15),  # Q1
            datetime(year, 6, 15),  # Q2
            datetime(year, 9, 15),  # Q3
            datetime(year, 12, 15),  # Q4
        ]

        for date in sample_dates:
            try:
                self._scrape_chart_for_date(date, db, access_token)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to scrape chart for {date}: {e}")
                continue

    def _scrape_chart_for_date(
        self, date: datetime, db: Session, access_token: str = None
    ):
        """Scrape Billboard Hot 100 chart for a specific date"""
        # Check if we already have data for this date
        existing = (
            db.query(BillboardChart)
            .filter(
                BillboardChart.chart_date == date,
                BillboardChart.chart_type == "hot-100",
            )
            .first()
        )

        if existing:
            logger.info(f"Chart data already exists for {date}")
            return

        # Format date for Billboard URL
        date_str = date.strftime("%Y-%m-%d")
        url = f"{self.base_url}/{date_str}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            chart_items = self._parse_chart_items(soup)

            if not chart_items:
                logger.warning(f"No chart items found for {date}")
                return

            # Store chart data
            for item in chart_items:
                chart_entry = BillboardChart(
                    chart_date=date,
                    chart_type="hot-100",
                    position=item["position"],
                    track_name=item["track_name"],
                    artist_name=item["artist_name"],
                )

                # Try to find Spotify track ID and audio features
                if access_token:
                    spotify_data = self._get_spotify_data(
                        item["track_name"], item["artist_name"], access_token
                    )
                    if spotify_data:
                        chart_entry.spotify_track_id = spotify_data["id"]
                        # Add audio features if available
                        features = spotify_data.get("audio_features")
                        if features:
                            chart_entry.acousticness = features.get("acousticness")
                            chart_entry.danceability = features.get("danceability")
                            chart_entry.energy = features.get("energy")
                            chart_entry.instrumentalness = features.get(
                                "instrumentalness"
                            )
                            chart_entry.liveness = features.get("liveness")
                            chart_entry.loudness = features.get("loudness")
                            chart_entry.speechiness = features.get("speechiness")
                            chart_entry.tempo = features.get("tempo")
                            chart_entry.valence = features.get("valence")
                            chart_entry.key = features.get("key")
                            chart_entry.mode = features.get("mode")
                            chart_entry.time_signature = features.get("time_signature")

                db.add(chart_entry)

            db.commit()
            logger.info(f"Stored {len(chart_items)} chart entries for {date}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch Billboard chart for {date}: {e}")
        except Exception as e:
            logger.error(f"Error processing chart for {date}: {e}")

    def _parse_chart_items(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse chart items from Billboard HTML"""
        chart_items = []

        # Billboard's HTML structure can change, so we'll try multiple selectors
        selectors = [
            'div[class*="chart-list-item"]',
            'li[class*="chart-list__element"]',
            'div[class*="o-chart-results-list__item"]',
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                break

        if not items:
            # Fallback: try to find any elements with chart-related classes
            items = soup.find_all(
                ["div", "li"], class_=lambda x: x and "chart" in x.lower()
            )

        for i, item in enumerate(items[:100]):  # Top 100
            try:
                # Try to extract track and artist information
                track_name = self._extract_track_name(item)
                artist_name = self._extract_artist_name(item)

                if track_name and artist_name:
                    chart_items.append(
                        {
                            "position": i + 1,
                            "track_name": track_name.strip(),
                            "artist_name": artist_name.strip(),
                        }
                    )

            except Exception as e:
                logger.debug(f"Failed to parse chart item {i}: {e}")
                continue

        # If we couldn't parse the modern format, try a simpler approach
        if not chart_items:
            chart_items = self._fallback_parse(soup)

        return chart_items

    def _extract_track_name(self, item) -> str:
        """Extract track name from chart item"""
        selectors = [
            'h3[class*="c-title"]',
            'h3[class*="chart-element__information__song"]',
            'div[class*="chart-element__information__song"]',
            ".chart-element__information__song",
            "h3",
            ".song-title",
        ]

        for selector in selectors:
            element = item.select_one(selector)
            if element:
                return element.get_text().strip()

        return ""

    def _extract_artist_name(self, item) -> str:
        """Extract artist name from chart item"""
        selectors = [
            'span[class*="c-label"]',
            'span[class*="chart-element__information__artist"]',
            'div[class*="chart-element__information__artist"]',
            ".chart-element__information__artist",
            "span",
            ".artist-name",
        ]

        for selector in selectors:
            element = item.select_one(selector)
            if element:
                return element.get_text().strip()

        return ""

    def _fallback_parse(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Fallback parsing method for older Billboard formats"""
        chart_items = []

        # Try to find text patterns that look like chart entries
        text_content = soup.get_text()
        lines = text_content.split("\n")

        current_position = 1
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for patterns like "Artist - Song" or "Song by Artist"
            if " - " in line and len(line.split(" - ")) == 2:
                parts = line.split(" - ")
                artist_name = parts[0].strip()
                track_name = parts[1].strip()

                if len(artist_name) > 0 and len(track_name) > 0:
                    chart_items.append(
                        {
                            "position": current_position,
                            "track_name": track_name,
                            "artist_name": artist_name,
                        }
                    )
                    current_position += 1

                    if current_position > 100:
                        break

        return chart_items

    def _get_spotify_data(
        self, track_name: str, artist_name: str, access_token: str
    ) -> Dict[str, Any]:
        """Get Spotify track data and audio features"""
        try:
            # Search for the track on Spotify
            query = f"track:{track_name} artist:{artist_name}"
            search_results = self.spotify_client.search_tracks(
                access_token, query, limit=1
            )

            if not search_results:
                # Try a simpler search
                query = f"{track_name} {artist_name}"
                search_results = self.spotify_client.search_tracks(
                    access_token, query, limit=1
                )

            if search_results:
                track = search_results[0]
                track_id = track["id"]

                # Get audio features
                audio_features = self.spotify_client.get_audio_features(
                    access_token, [track_id]
                )

                return {
                    "id": track_id,
                    "audio_features": audio_features[0] if audio_features else None,
                }

        except Exception as e:
            logger.debug(
                f"Failed to get Spotify data for {track_name} by {artist_name}: {e}"
            )

        return None

    def get_sample_data(self, db: Session) -> List[Dict[str, Any]]:
        """Get sample Billboard data for testing (when scraping fails)"""
        sample_tracks = [
            {
                "track_name": "Billie Jean",
                "artist_name": "Michael Jackson",
                "year": 1983,
            },
            {"track_name": "Like a Virgin", "artist_name": "Madonna", "year": 1984},
            {"track_name": "Take On Me", "artist_name": "a-ha", "year": 1985},
            {"track_name": "Walk This Way", "artist_name": "Run-D.M.C.", "year": 1986},
            {
                "track_name": "Sweet Child O' Mine",
                "artist_name": "Guns N' Roses",
                "year": 1988,
            },
            {"track_name": "Like a Prayer", "artist_name": "Madonna", "year": 1989},
            {"track_name": "Vogue", "artist_name": "Madonna", "year": 1990},
            {
                "track_name": "Smells Like Teen Spirit",
                "artist_name": "Nirvana",
                "year": 1991,
            },
            {
                "track_name": "I Will Always Love You",
                "artist_name": "Whitney Houston",
                "year": 1992,
            },
            {"track_name": "Dreamlover", "artist_name": "Mariah Carey", "year": 1993},
            {"track_name": "I Swear", "artist_name": "All-4-One", "year": 1994},
            {"track_name": "Waterfalls", "artist_name": "TLC", "year": 1995},
            {"track_name": "Macarena", "artist_name": "Los Del Rio", "year": 1996},
            {
                "track_name": "Candle in the Wind 1997",
                "artist_name": "Elton John",
                "year": 1997,
            },
            {
                "track_name": "The Boy Is Mine",
                "artist_name": "Brandy & Monica",
                "year": 1998,
            },
            {"track_name": "Believe", "artist_name": "Cher", "year": 1999},
            {"track_name": "Breathe", "artist_name": "Faith Hill", "year": 2000},
        ]

        # Store sample data if no data exists
        existing_count = db.query(BillboardChart).count()
        if existing_count == 0:
            logger.info("Adding sample Billboard data")
            for track in sample_tracks:
                chart_entry = BillboardChart(
                    chart_date=datetime(track["year"], 6, 15),
                    chart_type="hot-100",
                    position=1,
                    track_name=track["track_name"],
                    artist_name=track["artist_name"],
                )
                db.add(chart_entry)

            db.commit()
            logger.info(f"Added {len(sample_tracks)} sample tracks")

        return sample_tracks
