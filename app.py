from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
import pymongo
import time
from flask_cors import CORS
from uuid import uuid4
import oss2
import json
import config

# initial
app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)
app.config["JSON_AS_ASCII"] = False

# Database
uri = config.uri
client = pymongo.MongoClient(uri)
db = client.test


# 上传图片
def uploadImg(type, pic):
    #  upload
    auth = oss2.Auth(config.OSS_API_ID,config.OSS_API_KEY )
    bucket = oss2.Bucket(auth, "http://oss-cn-shenzhen.aliyuncs.com", "web-music")
    filename = str(uuid4())
    bucket.put_object(f"{type}/{filename}.jpg", pic)
    return f"http://web-music.oss-cn-shenzhen.aliyuncs.com/{type}/{filename}.jpg"


# 自增ID
def getnextid(xxID):
    if len(list(db.counter.find({"_id": xxID}))):
        ret = db.counter.find_one_and_update(
            {"_id": xxID}, {"$inc": {"sequence_value": 1}}
        )
        nextid = ret["sequence_value"]
        return nextid
    else:
        db.counter.insert_one({"_id": xxID, "sequence_value": 10000})
        return "10000"


@app.route("/")
def hello_world():
    return "Hello, World!"


# 注册
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return jsonify({"status": 200, "msg": "/register"})
    else:
        collection = db.users
        user_name = request.json.get("user_name").lower()
        user_pwd = request.json.get("user_pwd")

        if list(collection.find({"user_name": user_name})):
            return jsonify({"status": 409, "msg": "用户名已经存在"})
        else:
            collection.insert_one(
                {
                    "user_name": user_name,
                    "user_pwd": bcrypt.generate_password_hash(user_pwd),
                    "user_nick": "默认昵称",
                    "user_sex": "未填写",
                    "user_pic": "https://web-music.oss-cn-shenzhen.aliyuncs.com/static/default_avatar.jpg",
                    "user_desc": "未填写",
                    "liked_music": [],
                    "follower":[],
                    "following":[],
                    "time": time.time(),
                }
            )
            return jsonify({"status": 201, "msg": "用户创建成功！"})


# 登录
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return jsonify({"status": 200, "msg": "/login"})
    else:
        user_name = request.json.get("user_name").lower()
        user_pwd = request.json.get("user_pwd")
        collection = db.users

        if list(collection.find({"user_name": user_name})):
            pwd = list(
                collection.find({"user_name": user_name}, {"_id": 0, "user_pwd": 1})
            )[0]["user_pwd"]
            if bcrypt.check_password_hash(pwd, user_pwd):
                return jsonify({"status": 200, "msg": "登录成功"})
            else:
                return jsonify({"status": 401, "msg": "登录失败"})


# 显示用户收藏的歌单
@app.route("/get/collected_musiclist", methods=["POST"])
def collected_musiclist():
    collection = db.musiclist
    user_name = request.json.get("user_name")
    myquery = {"followed_by": user_name}
    return json.dumps(list(collection.find(myquery, {"_id": 0})))


# 获取用户创建的歌单
@app.route("/get/created_musiclist", methods=["POST"])
def created_musiclist():
    collection = db.musiclist
    user_name = request.json.get("user_name")
    myquery = {"created_by": user_name}
    return json.dumps(list(collection.find(myquery, {"_id": 0})))


# 显示用户喜欢的音乐
@app.route("/get/liked_music", methods=["POST"])
def liked_music():
    collection = db.users
    user_name = request.json.get("user_name")
    myquery = {"user_name": user_name}
    return json.dumps(list(collection.find(myquery, {"liked_music": 1, "_id": 0})))


# 好友
@app.route("/get/friends", methods=["POST"])
def get_friends():
    collection = db.users
    user_name = request.json.get("user_name").lower()
    myquery = {"friends": user_name}
    return jsonify(str(list(collection.find(myquery, {"friends": 1, "_id": 0}))))


@app.route("/get/user", methods=["POST"])
def get_user():
    collection = db.users
    user_name = request.json.get("user_name").lower()
    myquery = {"user_name": user_name}
    return json.dumps(list(collection.find(myquery, {"user_pwd": 0, "_id": 0})))


# 获取用户的头像
@app.route("/get/user_pic", methods=["POST"])
def get_user_pic():
    collection = db.users
    user_name = request.json.get("user_name").lower()
    myquery = {"user_name": user_name}
    return json.dumps(list(collection.find(myquery, {"user_pic": 1, "_id": 0}))[0])


# 获取歌单封面
@app.route("/get/list_cover", methods=["POST"])
def get_list_cover():
    collection = db.musiclist
    l_id = request.json.get("l_id")
    myquery = {"l_id": l_id}
    return json.dumps(list(collection.find(myquery, {"list_cover": 1, "_id": 0}))[0])


# 创建歌曲评论
@app.route("/create/comment", methods=["post"])
def create_comment():
    collection = db.comment
    m_id = request.json.get("m_id")
    isReply = request.json.get("isReply")
    replyId = request.json.get("replyId")
    author = request.json.get("author")
    content = request.json.get("content")
    o_author = request.json.get("o_author")
    o_content = request.json.get("o_content")
    collection.insert_one(
        {
            "m_id": m_id,
            "isReply": isReply,
            "o_author": o_author,
            "o_content": o_content,
            "replyId": replyId,
            "author": author,
            "content": content,
            "c_id": str(uuid4()),
            "liked":[],
            "created_time": time.time(),
        }
    )

    return "201"


# 显示评论
@app.route("/get/comment", methods=["POST"])
def get_comment():
    collection = db.comment
    m_id = request.json.get("m_id")
    myquery = {"m_id": m_id}
    return json.dumps(list(collection.find(myquery, {"_id": 0})))


# 新建歌单
@app.route("/create/musiclist", methods=["POST"])
def create_musiclist():
    l_id = getnextid("list_id")
    user_name = request.json.get("user_name")
    list_name = request.json.get("list_name")
    db.users.update_one(
        {"user_name": user_name}, {"$addToSet": {"created_musiclist": l_id}}
    )
    db.musiclist.insert_one(
        {
            "l_id": l_id,
            "list_name": list_name,
            "music_ids": [],
            "list_desc": "",
            "created_by": user_name,
            "followed_by": [],
            "created_time": time.time(),
            "list_cover": "http://web-music.oss-cn-shenzhen.aliyuncs.com/avatar/a2139317-3319-4865-8dd8-eddfcc44c4f0.jpg",
        }
    )
    return "201"


# 更新歌单
@app.route("/update/musiclist", methods=["POST"])
def update_musiclist():
    list_name = request.form["list_name"]
    list_desc = request.form["list_desc"]
    l_id = request.form["l_id"]
    query = {
        "list_name": list_name,
        "list_desc": list_desc,
    }
    if len(dict(request.files)) != 0:
        pic = request.files["list_cover"].read()
        url = uploadImg("list_cover", pic)
        query["list_cover"] = url
    db.musiclist.find_one_and_update({"l_id": int(l_id)}, {"$set": query})
    return "201"


# 删除歌单     √
# todo 同时从用户的 created_music_lists 删除
@app.route("/delete/musiclist", methods=["POST"])
def delete_musiclist():
    l_id = request.json.get("l_id")
    user_name = request.json.get("user_name")
    db.musiclist.remove({"l_id": l_id}, {})
    db.users.find_one_and_update(
        {"user_name": user_name}, {"$pull": {"created_musiclist": l_id}}
    )
    return "201"


# 收藏别人的歌单 √
@app.route("/update/collected_music", methods=["POST"])
def collected_music():
    l_id = request.json.get("l_id")
    user_name = request.json.get("user_name")
    db.musiclist.find_one_and_update(
        {"l_id": l_id}, {"$addToSet": {"followed_by": user_name}}
    )
    db.users.find_one_and_update(
        {"user_name": user_name}, {"$addToSet": {"collected_music_list": l_id}}
    )
    return "201"


# 取消收藏歌单 √
@app.route("/update/cancel_collected_music", methods=["POST"])
def cancel_collectd_music():
    l_id = request.json.get("l_id")
    user_name = request.json.get("user_name")
    db.musiclist.find_one_and_update(
        {"l_id": l_id}, {"$pull": {"followed_by": user_name}}
    )
    db.users.find_one_and_update(
        {"user_name": user_name}, {"$pull": {"collected_music_list": l_id}}
    )
    return "201"


# 获取歌单详情
@app.route("/get/musiclist_detail", methods=["POST"])
def get_musiclist_detail():
    l_id = request.json.get("l_id")
    return json.dumps(list(db.musiclist.find({"l_id": l_id}, {"_id": 0})))


# 把音乐收藏到特定歌单
@app.route("/collect/music", methods=["POST"])
def collect_music():
    l_id = request.json.get("l_id")
    music_id = request.json.get("music_id")
    db.musiclist.find_one_and_update(
        {"l_id": l_id}, {"$addToSet": {"music_ids": music_id}}
    )
    return "201"


# 从歌单里删除一首歌
@app.route("/delete/music", methods=["POST"])
def delete_music():
    l_id = request.json.get("l_id")
    music_id = request.json.get("music_id")
    db.musiclist.find_one_and_update({"l_id": l_id}, {"$pull": {"music_ids": music_id}})
    return "201"


#  喜欢一首歌  √
@app.route("/update/like_music", methods=["POST"])
def like_music():
    music_id = request.json.get("music_id")
    user_name = request.json.get("user_name")
    db.users.find_one_and_update(
        {"user_name": user_name}, {"$addToSet": {"liked_music": music_id}}
    )
    return "201"


# 取消喜欢一首歌 √
@app.route("/update/dislike_music", methods=["POST"])
def dislike_music():
    music_id = request.json.get("music_id")
    user_name = request.json.get("user_name")
    db.users.find_one_and_update(
        {"user_name": user_name}, {"$pull": {"liked_music": music_id}}
    )
    return "201"


# 获取热门歌单 √
@app.route("/get/hot_musiclist", methods=["GET"])
def get_hot_musiclist():
    result = list(db.musiclist.find({}, {"_id": 0}))
    result = sorted(result, key=lambda x: len(x["followed_by"]))
    result.reverse()
    return json.dumps(result)


# 个人资料编辑
@app.route("/update/ucenter", methods=["POST"])
def update_ucenter():
    user_name = request.form["user_name"]
    user_nick = request.form["user_nick"]
    user_sex = request.form["user_sex"]
    user_desc = request.form["user_desc"]
    query = {
        "user_nick": user_nick, 
        "user_sex": user_sex,
        "user_desc": user_desc,
    }
    if len(dict(request.files)) != 0:
        pic = request.files["user_avatar"].read()
        url = uploadImg("avatar", pic)
        query["user_pic"] = url
    db.users.find_one_and_update({"user_name": user_name}, {"$set": query})
    return "201"


# @app.route('/get_profile', methods=['GET'])
# def get():
#     collection = db.users
#     return str(list(collection.find({"user_name": "hoon"})))


# 上传头像
@app.route("/update/avatar", methods=["POST"])
def update_avatar():
    user_name = request.form["user_name"]
    pic = request.files["avatar"].read()
    url = uploadImg("avatar", pic)
    db.users.find_one_and_update({"user_name": user_name}, {"$set": {"user_pic": url}})
    return url
# 点赞
@app.route("/update/comment/liked",methods=["POST"])
def update_comment_liked():
    user_name = request.json.get("user_name")
    c_id = request.json.get("c_id")
    db.comment.find_one_and_update({"c_id":c_id},{"$addToSet":{"liked":user_name}})
    return "201"
# 取消点赞
@app.route("/update/comment/disliked",methods=["POST"])
def update_comment_disliked():
    user_name = request.json.get("user_name")
    c_id = request.json.get("c_id")
    db.comment.find_one_and_update({"c_id":c_id},{"$pull":{"liked":user_name}})
    return "201"

# 关注/取消关注
@app.route("/update/follow",methods=["POST"])
def update_follow():
    following = request.json.get("following") 
    follower = request.json.get("follower")
    following_detail = list(db.users.find({"user_name":following},{"_id":0,"user_pwd":0,"liked_music":0,"created_musiclist":0,
    "collected_musiclist":0}))[0]
    follower_detail = list(db.users.find({"user_name":follower},{"_id":0,"user_pwd":0,"liked_music":0,"created_musiclist":0,
    "collected_musiclist":0}))[0]
    type = request.json.get("type")
    if(type == "follow"):
        db.users.find_one_and_update({"user_name":follower},{"$addToSet":{"following":following_detail}})
        db.users.find_one_and_update({"user_name":following},{"$addToSet":{"follower":follower_detail}})
    else:
        db.users.find_one_and_update({"user_name":follower},{"$pull":{"following":following}})
        db.users.find_one_and_update({"user_name":following},{"$pull":{"follower":follower}})
    return "201"


if __name__ == "__main__":
    app.run(debug=True)
