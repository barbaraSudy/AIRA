import json
import uuid
from datetime import datetime
import os
import logging

from langchain.tools import Tool
from langchain.utilities import GoogleSearchAPIWrapper

from actions.scraper import Scraper
from actions.llm_utils import create_chat_completion
from actions.answer_question import answer_question
from config import Config


CFG = Config()
search = GoogleSearchAPIWrapper()

# Set up google search


log = logging.getLogger(__name__)

class ResearchAgent:


    def __init__(self, question, websocket):
        """ Initializes the research assistant with the given question.
        Args: question (str): The question to research
        Returns: None
        """
        print('$$$$$$$$$$$ BLAH BLAH1')
        log.info('$$$$$$$$$$$ BLAH BLAH2')
        self.question = question
        self.search_results = []
        self.urls_to_scrape = []
        self.directory_name = uuid.uuid4().hex
        # Pay attention where the file is in the overall directory tree
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
        self.dir_path = os.path.dirname(f"./outputs/{self.directory_name}/")
        self.output_path = os.path.join(self.root_dir, "outputs", self.directory_name)
        os.makedirs(self.output_path, exist_ok=True)
        self.websocket = websocket
        
        def top_google_results(query):
            return search.results(query, CFG.google_results)
        self.google_search_tool = Tool(
            name="Google Search Snippets",
            description="Search Google for recent results.",
            func=top_google_results,
        )


    async def conduct_research(self):
        """ Conducts the research for the given question.
        Args: None
        Returns: str: The research for the given question
        """
        # Ask ChatGPT to create relevant search queries
        print("Conducting research")

        search_queries = await self.create_search_queries()
        for query in search_queries:
            print(f"Query: {query}")
            results = await self.get_search_results(query)
            print(f"Results {results}")
            self.search_results.extend(results)

        
        # Remove duplicate links in case similar queries return same results
        self.remove_duplicate_search_results()
        self.urls_to_scrape = [d["link"] for d in self.search_results if "link" in d]
        await self.websocket.send_json(
            {"type": "logs", "output": f"🕷️ Now I will try to scrape {len(self.urls_to_scrape)} urls."})
        # Scrape and save results as txt files to output folder
        scraper = Scraper()
        scraper.scrape_parallel(self.urls_to_scrape, self.output_path)
        await self.websocket.send_json(
            {"type": "logs", "output": f"✅ I was successful in scraping {len(os.listdir(self.output_path))} sites, now on to summarizing"})
        # Answer the question based on scraped results in output folder
        summary = answer_question(self.output_path, self.question)
        await self.websocket.send_json(
            {"type": "logs", "output": f"📝 Here is my summary:\n {summary}"})

        return summary


    async def create_search_queries(self):
        """ Creates the search queries for the given question.
        Args: None
        Returns: list[str]: The search queries for the given question
        """
        prompt = f"""Write exactly {CFG.google_searches} google search queries to search online that form an objective opinion from the following: 
        "{self.question}". You must respond with a list of strings in the following format: ["query 1", "query 2", "query 3", "query 4"]"""
        result = await self.call_agent(prompt)
        await self.websocket.send_json({"type": "logs", "output": f"🔎 I will conduct my research based on the following google searches: {result}."})
        
        return json.loads(result)

    async def get_search_results(self, query):
        print(f"Retrieving search results from google using query: {query}")
        return self.google_search_tool.run(query)
    
    def remove_duplicate_search_results(self):
        # Convert each JSON object to a string
        json_strings = [json.dumps(item, sort_keys=True) for item in self.search_results]

        # Use a set to keep unique JSON strings and filter out duplicates
        unique_json_strings = list(set(json_strings))

        # Convert the unique JSON strings back to JSON objects
        self.search_results = [json.loads(item) for item in unique_json_strings]

        return self.search_results

    async def call_agent(self, action, stream=False, websocket=None):
        messages = [{
            "role": "system",
            "content": "Current date and time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, {
            "role": "user",
            "content": action,
        }]
        answer = create_chat_completion(
            model=CFG.fast_llm_model,
            messages=messages,
            stream=stream,
            websocket=websocket,
        )
        return answer