#!/usr/bin/env python3
"""
Multi-Park Availability Tester - Test the logic with different parks
"""

import requests
import json
import logging
from datetime import datetime
import pytz
import os
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiParkTester:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = "https://reserve.bcparks.ca"
        self.timezone = pytz.timezone('America/Vancouver')

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Test parks that are more likely to have availability
        self.test_parks = {
            'alice-lake': {
                'name': 'Alice Lake Provincial Park',
                'keywords': ['alice lake', 'alice'],
                'urls': [
                    f"{self.base_url}/facility/alice-lake-provincial-park",
                    f"{self.base_url}/dayuse/registration?facility=alice-lake-provincial-park"
                ]
            },
            'cultus-lake': {
                'name': 'Cultus Lake Provincial Park',
                'keywords': ['cultus lake', 'cultus'],
                'urls': [
                    f"{self.base_url}/facility/cultus-lake-provincial-park",
                    f"{self.base_url}/dayuse/registration?facility=cultus-lake-provincial-park"
                ]
            },
            'golden-ears': {
                'name': 'Golden Ears Provincial Park',
                'keywords': ['golden ears', 'golden'],
                'urls': [
                    f"{self.base_url}/facility/golden-ears-provincial-park",
                    f"{self.base_url}/dayuse/registration?facility=golden-ears-provincial-park"
                ]
            },
            'Garibaldi': {
                'name': 'Garibaldi Provincial Park',
                'keywords': ['Garibaldi', 'Garibaldii'],
                'urls': [
                    f"{self.base_url}/facility/Garibaldi-provincial-park",
                    f"{self.base_url}/dayuse/registration?facility=Garibaldi-provincial-park"
                ]
            },
            'joffre': {
                'name': 'Joffre Lakes Provincial Park',
                'keywords': ['joffre', 'joffrey'],
                'urls': [
                    f"{self.base_url}/facility/joffre-lakes-provincial-park",
                    f"{self.base_url}/dayuse/registration?facility=joffre-lakes-provincial-park"
                ]
            }
        }
    
    def send_telegram(self, message):
        """Send telegram message (optional - only if credentials provided)"""
        if not self.bot_token or not self.chat_id:
            logger.info("No Telegram credentials - skipping notification")
            return True
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Telegram notification sent successfully")
                return True
            else:
                logger.error(f"❌ Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def save_debug_html(self, html_content, park_name, url):
        """Save HTML content for debugging"""
        timestamp = int(time.time())
        filename = f"debug_{park_name}_{timestamp}.html"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Source URL: {url} -->\n")
                f.write(f"<!-- Timestamp: {datetime.now()} -->\n\n")
                f.write(html_content)
            
            logger.info(f"💾 Saved debug HTML: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Failed to save debug HTML: {e}")
            return None
    
    def check_park_availability(self, park_key):
        """Check availability for a specific park"""
        park_info = self.test_parks[park_key]
        logger.info(f"\n🏞️ Testing: {park_info['name']}")
        logger.info("=" * 60)
        
        availability_found = False
        
        for url in park_info['urls']:
            try:
                logger.info(f"🔍 Checking URL: {url}")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully loaded ({len(response.text)} chars)")
                    
                    # Save HTML for debugging
                    self.save_debug_html(response.text, park_key, url)
                    
                    if self.parse_for_availability(response.text, url, park_info):
                        availability_found = True
                        break
                else:
                    logger.warning(f"⚠️ HTTP {response.status_code} for {url}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Error checking {url}: {e}")
                continue
            
            time.sleep(1)  # Be respectful
        
        return availability_found
    
    def parse_for_availability(self, html_content, source_url, park_info):
        """Parse HTML content for availability indicators"""
        try:
            now = datetime.now(self.timezone)
            soup = BeautifulSoup(html_content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Save a text version for easier debugging
            with open(f"debug_text_{park_info['name'].replace(' ', '_')}_{int(time.time())}.txt", 'w', encoding='utf-8') as f:
                f.write(f"Source URL: {source_url}\n")
                f.write(f"Timestamp: {now}\n")
                f.write("=" * 80 + "\n\n")
                f.write(page_text)
            
            # Check if this page mentions the park
            has_park_content = any(keyword in page_text for keyword in park_info['keywords'])
            
            logger.info(f"📝 Page content length: {len(page_text)} characters")
            logger.info(f"🎯 Park keywords found: {has_park_content}")
            
            if not has_park_content:
                logger.info(f"❌ No {park_info['name']} content found on this page")
                return False
            
            logger.info(f"✅ Found {park_info['name']} content, analyzing...")
            
            # Comprehensive availability indicators
            availability_indicators = [
                'available', 'book now', 'reserve now', 'select date', 
                'choose date', 'select time', 'purchase', 'add to cart',
                'book online', 'reservation available', 'make reservation',
                'day use pass', 'day pass available'
            ]
            
            unavailable_indicators = [
                'sold out', 'fully booked', 'no availability', 'unavailable',
                'no passes available', 'booking closed', 'not available',
                'waitlist only', 'no day use passes', 'passes sold out'
            ]
            
            # Check for text indicators
            found_availability_words = [ind for ind in availability_indicators if ind in page_text]
            found_unavailable_words = [ind for ind in unavailable_indicators if ind in page_text]
            
            logger.info(f"📊 Availability indicators found: {found_availability_words}")
            logger.info(f"📊 Unavailable indicators found: {found_unavailable_words}")
            
            # Look for booking buttons and form elements
            booking_buttons = soup.find_all(['button', 'a'], string=lambda text: 
                text and any(word in text.lower() for word in ['book', 'reserve', 'purchase', 'select']))
            
            date_inputs = soup.find_all(['input', 'select'], {'name': lambda x: x and 'date' in x.lower()})
            
            logger.info(f"🔘 Booking buttons found: {len(booking_buttons)}")
            logger.info(f"📅 Date inputs found: {len(date_inputs)}")
            
            if booking_buttons:
                logger.info("📝 Booking button texts:")
                for btn in booking_buttons[:3]:  # Show first 3
                    btn_text = btn.get_text(strip=True) if btn.get_text() else btn.get('title', 'No text')
                    logger.info(f"   - {btn_text}")
            
            # Decision logic
            has_availability_text = len(found_availability_words) > 0
            has_unavailable_text = len(found_unavailable_words) > 0
            has_booking_elements = len(booking_buttons) > 0 or len(date_inputs) > 0
            
            logger.info(f"\n🔍 ANALYSIS SUMMARY:")
            logger.info(f"   Availability text indicators: {has_availability_text}")
            logger.info(f"   Unavailable text indicators: {has_unavailable_text}")
            logger.info(f"   Booking form elements: {has_booking_elements}")
            
            # Make decision
            if (has_availability_text or has_booking_elements) and not has_unavailable_text:
                logger.info("🎉 AVAILABILITY DETECTED!")
                
                message = f"🏞️ <b>{park_info['name'].upper()} AVAILABILITY!</b> 🎉\n\n"
                message += f"📍 <b>Park:</b> {park_info['name']}\n"
                message += f"🎫 <b>Status:</b> Availability detected\n"
                message += f"🔗 <b>URL:</b> {source_url}\n"
                message += f"⏰ <b>Time:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                if found_availability_words:
                    message += f"📝 <b>Found:</b> {', '.join(found_availability_words[:3])}\n"
                if booking_buttons:
                    message += f"🔘 <b>Buttons:</b> {len(booking_buttons)} booking elements\n"
                
                message += f"\n🏃‍♂️ <b>Go check it out!</b>"
                
                self.send_telegram(message)
                return True
            
            elif has_unavailable_text:
                logger.info("❌ Park confirmed unavailable")
                return False
            
            else:
                logger.info("❓ Park availability status unclear")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error parsing content: {e}")
            return False
    
    def test_all_parks(self):
        """Test availability detection with all parks"""
        logger.info("🚀 Starting Multi-Park Availability Test")
        logger.info("=" * 80)
        
        results = {}
        
        for park_key in self.test_parks.keys():
            try:
                availability_found = self.check_park_availability(park_key)
                results[park_key] = {
                    'name': self.test_parks[park_key]['name'],
                    'availability_found': availability_found
                }
                
                logger.info(f"Result: {'✅ AVAILABLE' if availability_found else '❌ NOT AVAILABLE'}")
                
            except Exception as e:
                logger.error(f"❌ Failed to test {park_key}: {e}")
                results[park_key] = {
                    'name': self.test_parks[park_key]['name'],
                    'availability_found': False,
                    'error': str(e)
                }
            
            logger.info("-" * 40)
            time.sleep(2)  # Be respectful between requests
        
        # Summary
        logger.info("\n📊 FINAL RESULTS SUMMARY:")
        logger.info("=" * 80)
        
        available_parks = []
        unavailable_parks = []
        error_parks = []
        
        for park_key, result in results.items():
            if 'error' in result:
                error_parks.append(result['name'])
                logger.info(f"❌ ERROR: {result['name']}")
            elif result['availability_found']:
                available_parks.append(result['name'])
                logger.info(f"✅ AVAILABLE: {result['name']}")
            else:
                unavailable_parks.append(result['name'])
                logger.info(f"⭕ NOT AVAILABLE: {result['name']}")
        
        # Send summary via Telegram
        summary_msg = f"📊 <b>Multi-Park Test Complete</b>\n\n"
        summary_msg += f"✅ <b>Available ({len(available_parks)}):</b>\n"
        for park in available_parks:
            summary_msg += f"  • {park}\n"
        
        summary_msg += f"\n⭕ <b>Not Available ({len(unavailable_parks)}):</b>\n"
        for park in unavailable_parks:
            summary_msg += f"  • {park}\n"
        
        if error_parks:
            summary_msg += f"\n❌ <b>Errors ({len(error_parks)}):</b>\n"
            for park in error_parks:
                summary_msg += f"  • {park}\n"
        
        summary_msg += f"\n⏰ <b>Test completed:</b> {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.send_telegram(summary_msg)
        
        logger.info("\n🏁 Test completed! Check the generated debug files for detailed analysis.")

def main():
    try:
        logger.info("🚀 Initializing Multi-Park Tester...")
        tester = MultiParkTester()
        tester.test_all_parks()
        
    except Exception as e:
        error_msg = f"💥 Fatal error: {e}"
        print(error_msg)
        logger.error(error_msg)

if __name__ == "__main__":
    main()