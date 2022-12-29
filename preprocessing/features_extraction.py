import pandas as pd
from sklearn.preprocessing import StandardScaler


class FeaturesExtraction:

    def __init__(self, attributes, extract_attr=False, turn_to_numeric=False, scale=False):
        """
        :param attributes: as read from node_attributes file (dictionary)
        :param extract_attr:
        :param turn_to_numeric:
        """
        self.attributes = self.turn_to_dataframe(attributes)
        if extract_attr:
            self.__extract_features(attributes)
        if turn_to_numeric:
            self.__turn_to_numeric()
        if scale:
            self.__scale()

    def turn_to_dataframe(self, attributes):
        return pd.DataFrame(attributes).transpose()

    def __extract_features(self, attributes):
        """Preprocessing and extraction of new features from node attributes."""
        self.attributes["verified"] = attributes["verified"].apply(lambda item: 1 if item else 0)
        self.attributes["party"] = attributes["party"].astype('category')

        self.attributes["followers_to_following"] = attributes.apply(
            lambda x: x['followers'] / x['following'] if x['following'] != 0 else 0, axis=1)

        self.attributes["average_tweets_per_day"] = attributes["total_tweets"] / attributes["twitter_age"]

        self.attributes["average_list_per_day"] = attributes["lists"] / attributes["twitter_age"]

        self.attributes["total_tweets"] = attributes.apply(
            lambda x: x['total_tweets'] / x['lists'] if x['lists'] != 0 else 0, axis=1)

        self.attributes["followers_per_day"] = attributes["followers"] / attributes["twitter_age"]

        self.attributes["total_tweets"] = attributes["following"] / attributes["twitter_age"]

        self.attributes["followers_per_age"] = attributes["following"] / attributes["twitter_age"]

        self.attributes["following_per_age"] = attributes["following"] / attributes["twitter_age"]

        self.attributes['tweets_per_party_number'] = attributes.groupby(['party'])['total_tweets'].transform('sum')

        self.attributes['lists_per_party_number'] = attributes.groupby(['party'])['total_tweets'].transform('sum')

        self.attributes["percentage_tweets_of_party"] = attributes["total_tweets"] / attributes['tweets_per_party_number']

        self.attributes["percentage_list_of_party"] = attributes["total_tweets"] / attributes['lists_per_party_number']

        self.attributes.drop(['tweets_per_party_number', 'lists_per_party_number'], axis=1, inplace=True)


    def __turn_to_numeric(self):
        self.attributes['verified'] = self.attributes['verified'].astype(int)
        self.attributes = pd.get_dummies(self.attributes, prefix=['party'], columns=['party'], drop_first=True)

    def __scale(self):
        scaler = StandardScaler()
        self.attributes[self.attributes.columns] = \
            scaler.fit_transform(self.attributes[self.attributes.columns])