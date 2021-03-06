import re
import unicodedata
import warnings
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean

import es_core_news_md  # spaCy pretrained model
import nltk
import spacy

from src.log_config import logger

try:
    from nltk.corpus import stopwords
except:
    nltk.download('stopwords')
    from nltk.corpus import stopwords

try:
    from nltk.stem import WordNetLemmatizer
except:
    nltk.download('wordnet')
    from nltk.stem import WordNetLemmatizer


class TwitterProcessor:
    # TODO: revisar idioma del lemmatizer. Configuración de idioma.
    def __init__(
        self, counter=Counter(), popcounter=Counter(), lemmatizer=WordNetLemmatizer()
    ):

        self.__counter = counter
        self.__popCounter = popcounter
        self.lemmatizer = lemmatizer
        self.punctuation = "¡!\"$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        self.stopWords = set(stopwords.words("spanish") + stopwords.words("english"))
        print("loading spaCy model: es_core_news_md")
        self.nlp = es_core_news_md.load()

    def __repr__(self):
        return f"""
        TweetsProcessor object:
        Counter: {self.__counter}
        Pop Counter: {self.__popCounter}
        Lemmatizer: {self.lemmatizer}
        """

    def __str__(self):
        return f"TweetsProcessor object"

    def addStopWords(self, lst):
        self.stopWords.update(set(lst))
        return f"Added to stopwords: {lst}"

    def tweetTokenizer(self, tweet_text):
        """
        Makes lowercase.
        Removes punctuation, stopwords, urls & numerics.
        Lemmatize.
        Returns a list of tokens.
        """

        tweet = re.sub(r"http\S*", "", tweet_text)  # remove URLs
        tweet = (
            unicodedata.normalize("NFKD", tweet)
            .encode("ASCII", "ignore")
            .decode("utf-8")
        )  # remove accents
        words = (
            str(tweet)
            .translate(str.maketrans("", "", self.punctuation))
            .lower()
            .split()
        )  # lowercase & punctuation
        token_list = [
            self.lemmatizer.lemmatize(word)
            for word in words
            if word not in self.stopWords and not word.isnumeric() and len(word) > 2
        ]  # lemmatizee, remove numerics & remove tokens with less than 3 letters.

        logger.info(f"Tokens created: {token_list}")

        return token_list

    @property
    def counter(self):
        return self.__counter

    def updateCounter(self, token_list):
        self.counter.update(token_list)
        return self.__counter

    @property
    def popCounter(self):
        return self.__popCounter

    def updatepopCounter(self, token_list):
        self.popCounter.update(token_list)
        return self.__popCounter

    def toSpacyDocs(self, batch_of_tweets):
        with self.nlp.disable_pipes(self.nlp.pipe_names):
            docs = [
                doc
                for doc in self.nlp.pipe(
                    [
                        " ".join(self.tweetTokenizer(tweet.full_text))
                        for tweet in batch_of_tweets
                    ]
                )
                if doc.vector_norm
            ]
        return docs

    def similarityPipe(self, tweet_list, ref_docs):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            for tweet in tweet_list:
                if tweet.display_text_range != "[0,0]":
                    tweet_tokenized = " ".join(self.tweetTokenizer(tweet.full_text))
                    spacy_doc = self.nlp.make_doc(tweet_tokenized)
                    tweet.similarity = round(
                        mean(
                            [
                                spacy_doc.similarity(user_tweet)
                                for user_tweet in ref_docs
                            ]
                        ),
                        3,
                    )
        return [tweet for tweet in tweet_list if tweet.similarity > 0.7]

    def isActive(self, user):
        if (
            hasattr(user, "status")
            and (datetime.now() - user.status.created_at) < timedelta(days=14)
            and user.statuses_count > 50
            and user.default_profile_image == False
        ):
            return True
        return False


if __name__ == "__main__":
    p = TwitterProcessor()
    lst = ["x", "y", "z"]
    p.counter.update(lst)
    print(len(p.counter))
    p.popCounter.update(lst * int((3 + (2 * 0.3))))
    print(len(p.popCounter))
