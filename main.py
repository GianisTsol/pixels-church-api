from flask import Flask, request, render_template
import json
import threading
import pickle
from PIL import Image
import random
import time
import requests
import secrets

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjMwNjExNzQ4NTUxNjY4NTMxMyIsInNhbHQiOiJ3OVVxazJnQXV1Ulh0MDZUa2JqV2pRIn0.55z57-d86Z4J4xSF73ofbHXMHRCAW6Ronfe9rBIdo6Y"
# Where "token" is your token from earlier.
HEADERS = {"Authorization": f"Bearer {token}"}

projects = {}
keys = {}

pixels = ""
size = {}

id = 0

sleeping = True

try:
    with open('keys.pickle', 'rb') as handle:
            keys = pickle.load(handle)
except:
    print("couldnt load keys")
try:
    with open('projects.pickle', 'rb') as handle:
            projects = pickle.load(handle)
            print(projects)
except:
    print("couldnt load projects")

def new_api_key(name, level):
    generated_key = str(secrets.token_urlsafe(16))
    keys[generated_key] = {"name": name, "level": int(level), "score": 0}
    savekeys()
    return generated_key

def check_access(key):
    global keys
    if key in keys:
        return(keys[key]["level"])
    else:
        return False

def rgb2hex(r, g, b):
    return '{:02x}{:02x}{:02x}'.format(r, g, b)

class taskmsgr(threading.Thread):
    """docstring for taskmsgr."""

    def __init__(self):
        super(taskmsgr, self).__init__()
        self.tasks = {}
        self.pending = {}
        self.terminate = threading.Event()

    def create_tasks(self, name, image, location):
        global id
        global canvas
        print("Creating tasks for: ", name, image, location)
        im = Image.open(image)
        imageSizeW, imageSizeH = im.size
        nonWhitePixels = []
        for i in range(0, imageSizeW):
            for j in range(0, imageSizeH):
                pixVal = im.getpixel((i, j))
                if pixVal[3] != 0:
                    canpix = canvas.getpixel((i+int(location[0]),j+int(location[1])))
                    if (canpix[0], canpix[1], canpix[2]) != (pixVal[0], pixVal[1], pixVal[2]):
                        id = len(self.tasks) + 1
                        self.tasks[id] = {"id": id, "source": name, "x": i+int(location[0]), "y": j+int(location[1]), "color": rgb2hex(pixVal[0], pixVal[1], pixVal[2])}

    def get_task(self):
        if len(self.tasks) > 1:
            i = random.randrange(len(self.tasks))
            self.pending[i] = self.tasks[i]
            del self.tasks[i]
            return self.pending[i]
        else:
            return "no tasks"

    def task_done(self, id):
        try:
            del self.pending[id]
        except:
            return("error")

    def run(self):
        while not self.terminate.is_set():
            time.sleep(20)
            global canvas
            global size
            result = requests.head("http://pixels.pythondiscord.com/get_pixels",headers=HEADERS)

            if "Cooldown-Reset" in result.headers:
                print("got a read cooldown... sleeping" + result.headers["cooldown-reset"])
                time.sleep(int(result.headers["cooldown-reset"]))

            if "Requests-remaining" in result.headers:
                if int(result.headers["Requests-Remaining"]) == 0:
                    print("Read waiting..." + result.headers["Requests-Reset"])
                    time.sleep(float(result.headers["Requests-Reset"]))
                else:
                    print("proceeding to recieve data...")

            result = requests.get("http://pixels.pythondiscord.com/get_pixels",headers=HEADERS)
            pixels = result.content

            result = requests.get("http://pixels.pythondiscord.com/get_size",headers=HEADERS)
            size = json.loads(result.content)
            global projects
            global id
            id = 0
            self.tasks = {}
            canvas = Image.frombytes('RGB', (size["width"], size["height"]), pixels)
            canvas.save("static/canvas.png")
            for i in projects.keys():
                try:
                    self.create_tasks(projects[i], projects[i]["image"], projects[i]["coords"])
                except Exception as e:
                    print("Error for tasks: " + str(projects[i]), e)


def savekeys():
    with open('keys.pickle', 'wb') as handle:
        pickle.dump(keys, handle, protocol=pickle.HIGHEST_PROTOCOL)

taskmanager = taskmsgr()
taskmanager.start()

app = Flask(__name__)

@app.route('/tasks', methods=['GET'])
def example():
   return json.dumps(taskmanager.tasks)

@app.route('/get_task', methods=['GET'])
def example1():
    return json.dumps(taskmanager.get_task())

@app.route('/task_done', methods=['POST'])
def example2():
    headers = request.headers
    if check_access(headers["Authentication"]) != False:
        taskmanager.task_done(int(headers["task-id"]))
        if "score" not in keys[headers["Authentication"]]:
            keys[headers["Authentication"]]["score"] = 1
            savekeys()
        else:
            keys[headers["Authentication"]]["score"] = keys[headers["Authentication"]]["score"] + 1
            savekeys()
        return '200'
    else:
        return "lol no"

@app.route('/get_projects', methods=['GET'])
def example3():
   return json.dumps(projects)

@app.route('/add_project', methods=['POST'])
def new_project():
    if check_access(request.headers["Authentication"]) == 2:
        projects[request.headers["project-name"]] = {"image": request.headers["project-image"], "coords": (int(request.headers["project-coords-x"]), int(request.headers["project-coords-y"]))}
        with open('projects.pickle', 'wb') as handle:
            pickle.dump(projects, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return projects
    else:
        return("Fuck you, cunt")


@app.route('/del_project', methods=['POST'])
def del_project():
    headers = request.headers
    if check_access(headers["Authentication"]) == 2:
        if "project-name" in headers:
            del projects[headers["project-name"]]
            return projects
    else:
        return("Fuck you, cunt")

@app.route('/new_key', methods=['POST'])
def new_key():
    print("Who da faq makin a key")
    if check_access(request.headers["Authentication"]) == 2:
        savekeys()
        return new_api_key(request.headers["key-name"], request.headers["key-level"]), 200
    else:
        return("Fuck you")


@app.route('/del_key', methods=['POST'])
def del_key():
    headers = request.headers
    if check_access(headers["Authentication"]) == 2:
            del keys[headers["other-key"]]
            return keys, '200'
    else:
        return("Fuck you"), '404'

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Welcome', members=keys, projects=projects)

app.run(host="0.0.0.0")
