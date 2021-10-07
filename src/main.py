'''
File name: main.py
Author: Oskar Hallström
Date created: 19/07/2021
Date last modified: 08/10/2021
Python Version: 3.8
'''
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy as np
from sklearn import cluster as skc
import spotify_helpers as sh

# Setting constants
MIN_THRESHOLD = 10
SHOULD_DELETE_PREVIOUS = True
ATTRIBUTE_LABELS = [
    ('valence',1),
    ('energy',1),
    ('acousticness',1),
    ('danceability',1),
    ('instrumentalness',1),
    ('speechiness', 1),
    ('tempo', 1/150),
    ('mode', 1)
    ]
PLAYLIST_DESCRIPTION = 'Automatically generated playlist by clustering of my liked songs.'


if __name__ == '__main__':
    # initialize client and get id of current user
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id="b049aec063a34f9a82736498da19de3f",
            client_secret="",
            redirect_uri="http://localhost/",
            scope="user-library-read playlist-modify-private playlist-read-private playlist-modify-public user-follow-modify"))
    user = sp.me()['id']
    
    # get all the attributes, ids and names of all saved songs
    (attributes, ids, names) = sh.get_features_of_saved_songs(sp, ATTRIBUTE_LABELS)

    # create the model and the clusters
    model = skc.AgglomerativeClustering(
        n_clusters=None,
        linkage='complete',
        distance_threshold=0.35
        )
    model.fit(attributes)

    #add track_ids to each cluster
    clusters = [[] for i in range(model.n_clusters_)]
    clusters_attributes = [[] for i in range(model.n_clusters_)]
    clusters_names = [[] for i in range(model.n_clusters_)]
    for idx, label in enumerate(model.labels_):
        clusters[label].append(ids[idx])
        clusters_attributes[label].append(attributes[idx])
        clusters_names[label].append(names[idx])

    #filter away clusters smaller than MIN_THRESHOLD and get their names
    playlists_to_create = []
    for i in range(model.n_clusters_):
        # filter away too small clusters
        if len(clusters[i]) > MIN_THRESHOLD:
            name = sh.get_playlist_name(np.array(clusters_attributes[i]), clusters_names[i])
            playlists_to_create.append((name, clusters[i]))

    if SHOULD_DELETE_PREVIOUS:
        sh.delete_previously_generated_lists(sp, PLAYLIST_DESCRIPTION)

    #create playlists
    for name, _ in playlists_to_create:
        sh.create_playlist(sp, user, name, PLAYLIST_DESCRIPTION)

    #get ids of created playlists
    playlists = sp.current_user_playlists()
    playlist_ids = {}
    for i, playlist in enumerate(playlists['items']):
        if playlist['description'] == PLAYLIST_DESCRIPTION:
            playlist_ids[playlist['name']] = playlist['id']

    #add tracks to the created playlists
    print("Creating the following playlists: ")
    for playlist in playlists_to_create:
        print(playlist[0])
        sh.add_tracks(sp, user, playlist[0], playlist[1], playlist_ids[playlist[0]], 0)
