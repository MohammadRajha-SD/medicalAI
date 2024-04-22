import nltk
import json
import random
import tensorflow as tf
import matplotlib.pyplot as plt
from skimage.transform import resize
import numpy as np

# NLP
#########################################################################
with open("doctor/static/NLP/intents.json") as json_data:
    intents = json.load(json_data)

words = []
classes = []
documents = []
ignore_words = ['?', '.']
for intent in intents['intents']:
    for pattern in intent['patterns']:
        w = nltk.word_tokenize(pattern)
        words.extend(w)
        documents.append((w, intent['tag']))
        if intent['tag'] not in classes:
            classes.append(intent['tag'])

stemming = nltk.stem.lancaster.LancasterStemmer()
words = [stemming.stem(w.lower()) for w in words if w not in ignore_words]
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))


def clean_up_sentence(sentence):
    # It Tokenize or Break it into the constituents parts of Sentence.
    sentence_words = nltk.word_tokenize(sentence)
    # Stemming means to find the root of the word.
    sentence_words = [stemming.stem(word.lower()) for word in sentence_words]
    return sentence_words


# Return the Array of Bag of Words: True or False and 0 or 1 for each word of bag that exists in the Sentence
def bow(sentence, word, show_details=False):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(word)

    for s in sentence_words:
        for i, k in enumerate(word):
            if k == s:
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" % k)
    return bag


ERROR_THRESHOLD = 0.25


def classify(sentence):
    # Prediction or To Get the Possibility or Probability from the Model
    model_nlp = tf.keras.models.load_model("doctor/static/NLP/chatbot.h5")
    bow_representation = bow(sentence, words)
    bow_representation_np = np.array([bow_representation])

    results = model_nlp.predict(bow_representation_np)[0]
    # Exclude those results which are Below Threshold
    results = [[i, r] for i, r in enumerate(results) if r > ERROR_THRESHOLD]
    # Sorting is Done because heigher Confidence Answer comes first.
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append((classes[r[0]], r[1]))  # Tuppl -> Intent and Probability
    return return_list


def response(sentence):
    results = classify(sentence)
    # That Means if Classification is Done then Find the Matching Tag.
    if results:
        # Long Loop to get the Result.
        while results:
            for i in intents['intents']:
                # Tag Finding
                if i['tag'] == results[0][0]:
                    # Random Response from High Order Probabilities
                    return random.choice(i['responses'])


def diagnose_text(result):
    if result > 0.88:
        return "Malignant! Please prepare the surgical plan as soon as possible!"
    elif result < 0.65:
        return "Not Malignant. Stay safe and keep a healthy living style."
    else:
        return "There is a potential for malignancy, please ask experts for further instructions."


# CNN
#########################################################################
def preprocess(pixels):
    stretch = np.std(pixels)
    pixels /= stretch
    mean = np.mean(pixels)
    pixels -= mean


def dcnn(path):
    image = plt.imread(path)
    image = resize(image, output_shape=(256, 256, 3))
    image_test = [image]
    image_test = np.asarray(image_test, dtype=np.float64)
    preprocess(image_test)

    model_dcnn3 = tf.keras.models.load_model("doctor/static/CNN/DCNN3.h5", compile=False)
    picture = np.expand_dims(image_test[0], axis=0)
    result = model_dcnn3.predict(picture)
    return result[0][0]


def dense(path):
    image = plt.imread(path)
    image = resize(image, output_shape=(256, 256, 3))
    image_test = [image]
    image_test = np.asarray(image_test, dtype=np.float64)
    preprocess(image_test)

    model_dense = tf.keras.models.load_model("doctor/static/CNN/Dense.h5", compile=False)
    picture = np.expand_dims(image_test[0], axis=0)
    result = model_dense.predict(picture)
    return result[0][0]
