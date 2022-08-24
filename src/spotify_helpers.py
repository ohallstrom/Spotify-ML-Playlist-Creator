'''
File name: spotify_helpers.py
Author: Oskar Hallström
Date created: 08/10/2021
Date last modified: 08/10/2021
Python Version: 3.8
'''
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy as np

def get_features_of_saved_songs(client, attribute_labels):
    """
    Gets features of all saved songs in the user's library
    :param client: Spotify API client
    :param attribute_labels: list of song attributes to get
    :return: 
        - attributes - list of attributes of saved songs
        - ids - list of ids of saved songs
        - names - list of names of saved songs
    """
    offset = 0
    list_attributes = []
    list_ids = []
    list_names = []

    while True:
        songs = client.current_user_saved_tracks(limit=50, offset=offset)['items']

        if len(songs) == 0:
            break

        ids = [i['track']['id'] for i in songs]
        names = [i['track']['name'] for i in songs]
        features = client.audio_features(ids)
        attributes = np.ndarray(shape=(len(ids), len(attribute_labels)))
        offset += 50

        for j, feature in enumerate(features):
            for i, label in enumerate(attribute_labels):
                if feature == None:
                    print("Was not possible to get attributes from " + names[i])
                    attributes[j,i] = 0
                else:
                    attributes[j,i] = feature[label[0]] * label[1]

        list_attributes.append(attributes)
        list_ids.append(ids)
        list_names.append(names)
    return (np.ma.concatenate(list_attributes), np.ma.concatenate(list_ids), np.ma.concatenate(list_names))

def delete_previously_generated_lists(client, description):
    """
    Deletes playlists with matching description as well
    as empty playlists with names starting with "Vibes of"
    :param client: Spotify API client
    :param description: String used for playlist descriptions
    """
    offset = 0

    while True:
        playlists = client.current_user_playlists(limit=50, offset=offset)['items']
        if len(playlists) == 0:
            break

        for playlist in playlists:
            if playlist['description'] == description:
                client.current_user_unfollow_playlist(playlist['id'])
                print("Playlist {} has been erased.".format(playlist['name']))
            elif playlist['name'][:11] == "AI-Vibes of":
                client.current_user_unfollow_playlist(playlist['id'])
                print("Playlist {} has been erased.".format(playlist['name']))
        offset += 50

def create_playlist(client, user, name, description):
    '''
    Creates a private playlist according to the given parameters.
    :param client: Spotify API client
    :param user: String of the current user's user id
    :param name: String of the playlist name
    :param description: String used for playlist descriptions
    '''
    # Sometimes the description is not added to the playlist
    client.user_playlist_create(
        user=user,
        name=name,
        public=False,
        collaborative=False,
        description=description)

def get_playlist_name(attributes, names):
    """
    Gets the playlist name which is based on the name of the approximated medoid of the cluster.
    The medoid is approximated as the closest point to the centroid of the cluster.
    :param attributes: list of all the playlist's song attributes
    :param names: list of all the playlist's song names
    """
    centroid = attributes.mean(axis=0)
    medoid_idx = ((attributes - centroid) ** 2).sum(axis=1).argmin()
    return "AI-Vibes of " + names[medoid_idx]

def add_tracks(client, user, name, tracks, id, n_try):
    '''
    Adds specified tracks to an existing playlist.
    :param client: Spotify API client
    :param user: String of the current user's user id
    :param name: String of the playlist name
    :param tracks: list of all the ids of the tracks to add
    :param id: String of the playlist id
    :param n_try: int of maximum number of tries
    TODO: Find a more robust solutions for KeyErrors 
    '''
    print("Try number " + str(n_try))
    if n_try == 5:
        print("Maximum amount of tries has been used.")
        client.current_user_unfollow_playlist(id)
        print("Playlist " + name + " has been deleted.")
    else:
        try:
            client.user_playlist_add_tracks(
                user=user,
                playlist_id=id,
                tracks=tracks,
                position=None)
        except KeyError:
            print("An error occured in the creation of " + name + ", let's try again!")
            add_tracks(client, user, name, tracks, id, n_try+1)