import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy as np
from sklearn import cluster as skc

### Variables to set by user
min_threshold = 10
should_delete_previous = True
###

# initialize client
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id="b049aec063a34f9a82736498da19de3f",
        client_secret="a181cae4c2dd4a7ab5c88eef0239edb7",
        redirect_uri="http://localhost/",
        scope="user-library-read ugc-image-upload playlist-modify-private playlist-read-private playlist-modify-public user-follow-modify"))
user = sp.me()['id']

# stores chosen attributes and corresponding coefficient
attribute_labels = [
    ('valence',1),
    ('energy',1),
    ('acousticness',1),
    ('danceability',1),
    ('instrumentalness',1),
    ('speechiness', 1),
    ('tempo', 1/150),
    ('mode', 1)
    ]

def getFeaturesOfSaves(client, attribute_labels):
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

def delete_previously_generated(description, client):
    offset = 0

    while True:
        playlists = client.current_user_playlists(limit=50, offset=offset)['items']
        if len(playlists) == 0:
            break

        for playlist in playlists:
            if playlist['description'] == description:
                client.current_user_unfollow_playlist(playlist['id'])
                print("Playlist {} has been erased.".format(playlist['name']))
            elif playlist['name'][:8] == "Vibes of" and playlist['tracks']['total']==0:
                client.current_user_unfollow_playlist(playlist['id'])
                print("Playlist {} has been erased.".format(playlist['name']))
        offset += 50

def getPlaylistName(attributes, names):
    """
    The playlist name is based on the name of the approximated medoid of the cluster.
    The medoid is approximated as the closest point to the centroid of the cluster.
    """
    centroid = attributes.mean(axis=0)
    medoid_idx = ((attributes - centroid) ** 2).sum(axis=1).argmin()
    return "Vibes of " + names[medoid_idx]

def addTracks(client, user, name, tracks, id, n_try):
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
            print("An error occured in the creation of " + playlist[0] + ", let's try again!")
            addTracks(client, user, name, tracks, id, n_try+1)


(attributes, ids, names) = getFeaturesOfSaves(sp, attribute_labels)

# create the model and the clusters
model = skc.AgglomerativeClustering(
    n_clusters=None,
    linkage='complete',
    distance_threshold=0.35
    )
model.fit(attributes)

#add track_ids to each cluster
clusters =[[] for i in range(model.n_clusters_)]
clusters_attributes =[[] for i in range(model.n_clusters_)]
clusters_names =[[] for i in range(model.n_clusters_)]
for idx, label in enumerate(model.labels_):
    clusters[label].append(ids[idx])
    clusters_attributes[label].append(attributes[idx])
    clusters_names[label].append(names[idx])

#filter away clusters smaller than min_threshold and get their names
playlists_to_create = []
for i in range(model.n_clusters_):
    # filter away too small clusters
    if len(clusters[i]) > min_threshold:
        name = getPlaylistName(np.array(clusters_attributes[i]), clusters_names[i])
        playlists_to_create.append((name, clusters[i]))



description = 'Automatically generated playlist by clustering of my liked songs.'
if should_delete_previous:
    delete_previously_generated(description, sp)

#create playlists
for name in playlists_to_create:
    sp.user_playlist_create(
    user=user,
    name=name[0],
    public=False,
    collaborative=False,
    description=description)

#get ids of created playlists
playlists = sp.current_user_playlists()
playlist_ids = {}
for i, playlist in enumerate(playlists['items']):
    if playlist['description'] == description:
        playlist_ids[playlist['name']] = playlist['id']

#add tracks to the created playlists
print("Creating the following playlists: ")
for playlist in playlists_to_create:
    print(playlist[0])
    addTracks(sp, user, playlist[0], playlist[1], playlist_ids[playlist[0]], 0)
