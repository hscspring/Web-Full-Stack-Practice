# Web Full Stack Practice：Docker + uWSGI + Celery + Django + Supervisor + React + Nginx + Https + Postgres + Redis

本项目主要介绍基于 Docker 的 Web 开发和部署（开发要求在改动代码时服务或页面能够实时发生变化）全流程，来源于日常项目，后端以 Django 为例，前端以 React 为例，使用到的其他模块也可以换成同类产品，比如 uWSGI 可以换成 Gunicorn，数据库可以换成 Mysql 等。我们将通过一个案例前后端分离介绍，这样容易理解。

## 目标

- docker-compose 启动前后端同时开发
- 本地开发 + 正式部署 Https
- Supervisor + uWSGI + Nginx 部署

> 特别说明：在前后端联合调试时比较方便，如果单个开发后端或前端，直接本地很多时候会更方便。
>
> 关于本地 Https，很多框架本来就是支持的，就不要像本文这么麻烦了。

## 环境

- MacOS Mojave 10.14
- Docker Desktop Community Version 2.0.0.2
    - Engine：18.09.1
    - Compose：1.23.2

## 产品

作为一名 NLP 算法工程师，我们决定做一个简单的 Language Model 的 Demo，前端用户输入一个词，返回一段自动生成的文本。

模型参考：[递归神经网络  |  TensorFlow](https://www.tensorflow.org/tutorials/sequences/recurrent#language_modeling)，使用张爱玲作品集的句子作为训练集，800 个句子，52750 字，跑了 150 个 epoch。

## 后端

后端部分主要包括：uWSGI、Celery、Django、Supervisor、Postgres 和 Redis，首先分别简单介绍一下这些模块的功能：

- uWSGI：[The uWSGI project — uWSGI 2.0 documentation](https://uwsgi-docs.readthedocs.io/en/latest/)，Web 服务器，针对后端服务。
- Celery：[Celery - Distributed Task Queue — Celery 4.2.0 documentation](http://docs.celeryproject.org/en/latest/)，分布式任务队列服务，针对后端耗时较长的执行任务，也可以让 Django 异步。
- Django：[The Web framework for perfectionists with deadlines | Django](https://www.djangoproject.com/)，Python 的 Web 开发框架。
- Supervisor：[Supervisor: A Process Control System — Supervisor 3.3.5 documentation](http://supervisord.org/)，进程管理工具，主要用于在一个容器启动多个服务。
- Postgres：数据库
- Redis：缓存数据库（本例中用于 Celery 消息管理）

### Step1: Postgres

首先把 db 设置好，如果这里需要用到 redis 也需要一并设置。

我们可以使用 `docker-compose up db`（在 `docker-compose.yml` 所在目录执行）只启动 db，然后在本地登陆 db 去创建用户，当然本地也可以直接使用 postgres 作为用户。**需要注意的是：host 地址是本机的 IP 地址**，Mac 可以使用 `ifconfig` 查看。

`psql -h 192.168.0.103 -U postgres`，密码就是启动时创建的超级用户的密码，登陆后最好是更改一下 postgres 的密码，因为环境变量的那个只是启动时用一下。

```sql
# create user
create user demo with password "demopassword";
# create db
create database demo;
# grant privileges
grant all privileges ON database demo to demo;
```

当然，你也可以直接使用 `docker run -it --rm --name mypsql -e POSTGRES_PASSWORD=password4superuser -p 5432:5432  -v ~/docker_volume/pg9.5:/var/lib/postgresql/data postgres:9.5` 启动 db，启动后可以更改 postgres 用户的密码。

这一步的主要目的就是创建用户和 db ，然后把 data 都映射出来，这样我们后端启动时，就可以通过配置文件连接到 db 了。

### Step2: Django

这块主要针对 Django 的流程和注意事项，熟悉或者不需要的可以跳过。

```bash
# 初始化项目
mkdir demo && cd "$_"
django-admin startproject demo_backend
cd demo_backend
# 创建一个 app
python manage.py startapp text_generator
```

到这一步基本的框架就有了，之后就是项目配置和具体代码的编写。一些 Keypoints：

- Python 环境及开发包管理：[pypa/pipenv: Python Development Workflow for Humans.](https://github.com/pypa/pipenv)
    - 创建虚拟环境：`pipenv --python 3.6.5 # 我的本地环境是 python 3.6.5` 
    - `pipenv shell` 可以进入虚拟环境，或使用 `pipenv run python xxx.py` 等于直接在虚拟环境中运行 `python xxx.py`，`pipenv install xx` 可以安装需要的依赖，或安装指定版本，比如本例：`pipenv install tensorflow==1.12.0`
    - **使用之前，将 Pipfile 中的 url 改成 https://pypi.douban.com/simple 或其他速度快的源**，Pipfile 能看到所有已安装的包

- 关于 settings：
    - 将 setting 分为 prod 和 dev 两个文件，分别设置开发和正式环境的参数，需要修改 `wsgi.py, manage.py` 以便 Django 能够找到配置文件
    - 一般每个 APP 下面都可能有配置文件，编写代码时最好改成可以统一在项目的 settings 这里覆盖。比如训练好的模型文件（详见配置文件 `settings/base.py`）可以映射出来，这样不但可以方便我们随时更新模型，而且也能减小 image 的大小。
- 关于 database：
    - 使用配置文件，这样本地开发完部署时只要在服务器用正式的配置文件即可
    - 如果使用 docker-compose，数据库的 host 是：192.168.65.2，而不是 127.0.0.1 或本机地址

涉及到代码相关或相应文件的，项目中均有注释，可直接查看相应文件。

### Step3: Celery+Redis

首先代码需要做相应的修改，可以直接查看代码文件。

本地开发环境配置方面需要注意的是：

- 在 `wsgi.py` 同目录（settings文件夹同目录）新建 `celery.py` 并配置，然后修改 `__init__.py`，再修改 `settings/base.py` 中的配置
- 启动 redis，运行：`celery -A demo_backend worker -l info` 即可

正式环境需要将其作为 daemon 启动，需要配置 conf：

- 在 `demo_backend/celery` 目录下，conf 最重要的两个配置是：`CELERY_APP="demo_backend"` 和 `CELERYD_CHDIR="/demo-backend"`，后者一般是 Dockerfile 后端 server 的根目录，也就是整个后端项目的根目录（settings 文件夹和 `celery.py` 的上级目录）；sh 主要就是把`DEFAULT_USER` 改成和 conf 一致。

    需要说明的是：这两个文件可以放在任何地方，因为它们最终都是要放到 `/etc/` 下面的。

- user 和 group 一般就选择 root，当然也可以自己创建 user 和 group，官方建议非 root，不过因为我们是在 docker 里面，所以 root 也没有太多问题。

    这里的原因是，root 用户出错时可能会对系统造成一些意想不到的错误，如果系统有其他服务可能会出问题，但我们的 docker 服务是隔离和相对独立的，所以个人觉得使用 root 问题不大；同样的问题在 uWSGI 那里也有。

> 这里需要说明的是：本例直接等后端返回结果再传给前端，没有使用异步，因为速度不是特别慢。如果需要异步，可以在 `task.get()` 之前马上将 task id 返给前端，然后由前端根据 task id 获取最终的结果，这样就变成了异步操作。

### Step4: uWSGI

按照配置文件配置，需要注意的是，这里**不用配置 daemon**。可以设置 server 为：`socket=app.sock` 或直接使用 http（docker 中不能使用 `app.sock`，因为文件不在一个容器内）。

需要注意的是，这个是在正式环境下使用的，如果在本地开发环境，直接用 `python manage.py runserver 0.0.0.0:8000` 启动服务即可。

相关参数详细说明可以参考：

- [How to use Django with uWSGI | Django documentation | Django](https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/uwsgi/) 
-  [Things to know (best practices and “issues”) READ IT !!! — uWSGI 2.0 documentation](https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html)
- [How to create a Django server running uWSGI, NGINX and PostgreSQL on AWS EC2 with Python 3.6](https://medium.freecodecamp.org/django-uwsgi-nginx-postgresql-setup-on-aws-ec2-ubuntu16-04-with-python-3-6-6c58698ae9d3)

### Step5: Supervisor

主要目的是把多个服务放在一个容器内启动，官方文档 [Run multiple services in a container | Docker Documentation](https://docs.docker.com/config/containers/multi-service_container/) 也有相应的介绍。关于 stopsignal 参数的说明，可以参考：[How to use supervisor fo start/stop uWSGI application? - Stack Overflow](https://stackoverflow.com/questions/19510195/how-to-use-supervisor-fo-start-stop-uwsgi-application)

### Step6: Dockerfile

接下来就是编写 Dockerfile 了，我们可以用一个 Dockerfile 同时满足本地开发和正式部署，主要通过 supervisor 不同的配置文件来实现，本地开发时还需要把整个目录映射出去，这样当文件内容发生变化时，服务会自动刷新。

运行 `docker-compose build app` 单独 build app，build 完成后可以通过 `docker-compose up db redis app` 来启动 db、redis 和后端服务，`docker-compose stop` 停止服务。需要注意的是：

- `backend.local.env` 中的 db host 和 redis host 都需要改为 192.168.65.2，这是 docker 服务的默认地址，否则无法连接到 db 和 redis。db host 也可以直接使用 `docker-compose.yml` 中 db 的 name（如本例中是：db）。
- 本地开发时，需要把整个项目目录映射出去。但在测试正式环境时不需要（注释掉 `docker-compose.yml line 29`），因为映射后容器里面目录的内容会被清空，以映射出来的目录为准了，而我们本地并没有设置 Celery 的 deamon；而且 uWSGI 也可能会报错，因为我们没有设置虚拟环境的目录。
- 本地开发时，command 要写成本地的 Supervisor 配置文件以替换 Docker 里面的正式配置文件。但在测试正式环境时要记得注释掉（`docker-compose.yml line 40`）。
- 容器启动后，需要通过 `docker exec -it app bash`（app 可以替换为 container id）进入后端容器内部执行系列命令，包括：
    - `python manage.py makemigrations` 生成 db 相关数据
    - `python manage.py migrate` 将生成的数据 migrate 到 db
    - `python manage.py createsuperuser` 可以创建管理后台的管理员
    - `python manage.py collectstatic ` 自动输出静态文件到项目根目录
- 本地开发时，log 会直接输出到屏幕。但在测试正式环境时，日志会映射出来到映射的目录（如本例的 `~/docker_volume/log/`），可以直接通过目录文件查看。

到这一步，后端部分就已经完成了，我们可以通过 http://127.0.0.1:8000/admin/ 登陆管理员，也可以通过 http://127.0.0.1:8000/api/ 查看 Rest Framework，或者通过调用 http://127.0.0.1:8000/api/generate/ 生成。后端代码修改后，服务会自动刷新。

## 前端

刚刚后端的访问是直接通过 ip 地址 + 端口执行的，正式环境中需要用 Nginx 做转发；开发环境下，我们只需用 localhost 直接访问即可。这里稍微有点麻烦的是本地 Https 的配置。

### React

前端我们使用 Facebook 的 [Create React App · Set up a modern web app by running one command.](https://facebook.github.io/create-react-app/)

```bash
npx create-react-app demo_frontend
cd demo_frontend
npm start
```

上面的代码即可创建一个 App 并启动前端页面，安装依赖直接用 `npm i xxx ` 即可，如果只是在开发环境下使用，可以 `npm i xxx --save-dev`，然后完成代码编写。

### Https

要想在本地开发时使用 https 有两个重要的步骤：

- 生成证书相关文件
- 配置 React

生成证书相关文件需要借助：[dakshshah96/local-cert-generator: 🚀 A set of scripts to quickly generate a HTTPS certificate for your local development environment.](https://github.com/dakshshah96/local-cert-generator)

- 前三步是让你的本机成为一个 “证书颁发机构”，将第二步生成的 rootCA.pem 双击添加后，都改为 “信任” 即可。如图所示：

    ![](http://qnimg.lovevivian.cn/blog-sslstep-1.jpeg)

- 第二步有几个需要注意的地方：

    - `Enter pass phrase for rootCA.key:` 输入一个自己定义的密码（要输三次），要记住，以后每次为域名生成证书时都需要输入
    - 后面的除了 `Common Name` 都可以回车跳过，这个是证书颁发机构的名称，输入 `Local Cert` 或 `My PC Cert` 之类的都可以

- 然后运行第四步生成 localhost 的证书，或者使用仓库中的 `g_ssl_for_domain.sh`：`./g_ssl_for_domain.sh localhost /path/to/store/ssl/file/`，两个参数分别是你网站的域名和生成 ssl 文件的存储目录。我们需要 `server.crt` 和 `server.key` 就可以了，为了方便之后的操作，我把这两个文件放到了 `demo_frontend/ssl.localhost` 目录下。

然后要配置 React，这里我们需要安装 [timarney/react-app-rewired: Override create-react-app webpack configs without ejecting](https://github.com/timarney/react-app-rewired)：`npm i react-app-rewired --save-dev`。

- 首先在项目根目录下创建一个 `config-overrides.js` 的文件，配置将在里面进行，详见配置文件。这里我们用了一下环境变量，指定 `server.crt, server.key` 的位置
- 然后根据官方说明，修改 `package.json`，将相应的 `react-scripts` 改为 `react-app-rewired`

最后就是 Dockerfile 的编写了，由于本地开发，所以这里会比较简单，只要有 node 环境即可。

然后我们就可以使用 `docker-compose up redis db app web` 来启动所有服务了，然后通过 `https://localhost:3000` 访问前端，我们可以看下证书，没错，是我们的 `My PC Cert` 颁发的。

![](http://qnimg.lovevivian.cn/blog-sslstep-3.jpeg)

尝试生成一句：

![](http://qnimg.lovevivian.cn/blog-sslstep-2.jpeg)

我们可以修改前端代码，由于目录映射页面会重新编译、自动刷新。最后记得 `npm run build` 生成静态文件。

### Nginx

[NGINX | High Performance Load Balancer, Web Server, & Reverse Proxy](https://www.nginx.com/) 一般会用在产品部署上，作为代理和静态资源服务器，接下来我们主要介绍如何在本地调试 Nginx。主要有以下几步：

- 生成域名的证书，我们随便用一个名字，比如 `naivegenerator.com`
- 编写 Nginx 配置文件
- 编写 Dockerfile 并 build image
- 修改 Host

生成域名证书时，需要将 `v3.ext` 中的 `DNS.1 = naivegenerator.com` 修改掉，然后执行 `sh createSelfSigned.sh` 即可生成新域名的证书，我们将其放在前端根目录的 ssl 目录下。

Nginx 配置文件我们主要编写 `nginx.proj.conf` 即可，各配置详细说明可以直接看文件，有个地方需要注意下，如果 location 块使用 `/xxx/` 时，`proxy_pass` 后面加斜杠和不加斜杠结果会不一样，举个例子：

```nginx
server
{
    listen 80;
    server_name: www.naivegenerator.com;
    location /api/ {
        proxy_pass http://127.0.0.1:8000; # 配置1
        proxy_pass http://127.0.0.1:8000/; # 配置2
    }
}
```

使用配置 1 时，请求 `http://www.naivegenerator.com/api/generate/` 时会被成功转到：`http://127.0.0.1:8000/api/generate/`，而使用配置 2 时，则会被转到：`http://127.0.0.1:8000/generate/`。请求静态文件也是一样，所以这里需要稍微注意下。

然后是编写 Dockerfile（最好创建并编写一下 `.dockerignore` 将 node modules 忽略掉），这里面有四个地方要强调一下：

- 正式部署时，一般需要先在服务器上放一个验证文件，能点击下载后才能获得 `server.key` 和 `server.crt`，比如 [SSL For Free - Free SSL Certificates in Minutes](https://www.sslforfree.com/)，但我们本地因为是自己电脑给的证书，所以这一步不需要。当然如果你采用其他的证书授予商，也可能有不同的要求。除了上面那个免费的 SSl 外，还有很多，大家可以上网搜一搜，比如：[Getting Started - Let's Encrypt - Free SSL/TLS Certificates](https://letsencrypt.org/getting-started/)。
- 关于 ARG 和 ENV 详细情况大家可以看一下官网，build image 时可以使用 arg。本例中，我们使用 `ENV BACKEND_HOST=${backend_host}` 设置了一个环境变量，变量值从 docker-compose 中 nginx build 的 arg 中取变量名为 `{backend_host}` 的变量，然后将该环境变量传入配置文件，让其生效。这么做的目的主要是因为本地 docker-compose up 后 Nginx 访问后端服务需要使用 `192.168.65.2`，而不是 `127.0.0.1`，正式部署时在 k8s 上可以使用后者。
- 前端的静态文件在运行 `npm run build` 后会自动生成 build 文件夹，我们在 `nginx.proj.conf` 中将其设置为主页的根目录；后端（admin 和 rest）的静态文件则需要后端用 `python manage.py collectstatic` 收集后在 Dockerfile 中复制到前端某个地址。需要说明的是，因为我们将这个 static 目录共享了，所以虽然我们把本地目录整个映射出去了，但登陆 app 容器运行上面的命令后本地依然看不到 static 下的文件。因为 docker 会自动创建一个 volume（只要运行 `docker volume ls` 就看到了），文件就在这共享的 volume 里（本例中位 demo_app_static）。那怎么办呢？有三种办法：
    - 注释掉共享的目录，重新启动运行；
    
    - 本地生成；
    
    - 找到文件的实际位置然后复制出来，关于 volume 的详细情况可以通过 `docker volume inspect demo_app_static` 查看，运行 `screen ~/Library/Containers/com.docker.docker/Data/vms/0/tty` 然后进入 inspect 的目录就可以看到了。注意需要运行一个 docker 才能复制，步骤如下:
    
        - `docker run -it --rm -v volume_name:/home_or_other_dir  container /bin/bash`
        - `docker cp container_name:/home_or_other_dir /your_local_path`
    
        因为这里的 volume 并没有在你 `docker-compose up` 起来的容器里，所以我们需要先将它映射到一个容器里再复制。
- 关于 Dockerfile 中 ENV 替换到 nginx 配置文件需要特别注意，可以参考这里：[configuration - nginx 'invalid number of arguments in "map" directive' - Stack Overflow](https://stackoverflow.com/questions/39968344/nginx-invalid-number-of-arguments-in-map-directive)

最后别忘了修改 host：`sudo vim /etc/hosts`，添加一行：`127.0.0.1 naivegenerator.com`，这样当我们访问 `naivegenerator.com` 时等于是访问了 `127.0.0.1`。

## 最终效果

重新 `docker-compose up redis db app nginx` 后我们可以打开 `https://naivegenerator.com`，然后输入 “爱情” 让模型随机生成，如图所示：

![](http://qnimg.lovevivian.cn/blog-sslstep-4.jpeg)

admin 网址：`https://naivegenerator.com/admin`，如图所示：

![](http://qnimg.lovevivian.cn/blog-sslstep-5.jpeg)

rest 网址：`https://naivegenerator.com/api`， 如图所示：

![](http://qnimg.lovevivian.cn/blog-sslstep-6.jpeg)

## 注意事项

- 如果 `docker-compose stop` 后还想把生成的 container 也删掉（因为各种报错我们可能会不停地 build，有时候之前的需要彻底删除），可以使用这个命令：`docker stop $(docker ps -a -q); docker rm $(docker ps -a -q); docker volume rm $(docker volume ls -qf dangling=true)`

- 由于本例把所有操作整合在一起了，有些童鞋如果想要了解每一步的细节，可以在本地把环境设置好，使用 docker-compose 单独 up 启动 db 和 redis，然后在本地操作后端交互。无论是 up 还是 stop，都须在 `docker-compose.yml` 所在目录执行。
- docker-compose 中 build 之外的字段对 build 没有影响，build 主要受 Dockerfile 的影响；Dockerfile 如果名字不是 `Dockerfile` 需要指定文件名。
- 本例把 `backend.local.env` 和 `frontend.local.env` 一起上传了，但在正式项目中，大家务必把 `*.env` 添加到 `.gitignore` 中，这样信息就不会泄露了。
- 本例使用了 Celery 但后端代码并没有写成异步；同样使用了 Redis 但并未用在后端服务，而是用作了 Celery 的 Broker。
- 本例中的各个模块（Docker）除外都可以替换为同类其他产品，前后端自不必说，uWSGI 有 Guniron，Postgres 有 Mysql、MongoDB 等等，但我觉得基本思路是类似的，我们的目的是 Docker 化。
- 关于 Docker 操作的，台湾省一个同胞写的 [twtrubiks/docker-tutorial: Docker 基本教學 - 從無到有 Docker-Beginners-Guide 教你用 Docker 建立 Django + PostgreSQL 📝](https://github.com/twtrubiks/docker-tutorial) 还不错，另外官方文档也非常赞，所以我就没有废话了。我在他另一个项目里也学到了一些（第一个参考文献），推荐新手看看。
- 本项目可优化之处还有很多，比如 Redis 用于后端服务、比如异步操作、比如 uWSGI socket 方式等等，不一而足，还请大家结合自己的实际情况灵活使用。另外，各个部分深入后都会有另外一些坑，比如 postgres create db 的编码问题，我会在其他文章中分享，欢迎大家关注。

## 小结

本项目主要介绍基于 Docker 的 Web 全栈开发系列，看似东西很多，但其实每个地方都没有过多深入，项目也非常简单，所以适合 beginners。如果大家觉得看起来好像非常繁琐那也是正常的，因为确实会有一点繁琐，但只要仔细点理清每个地方其实并不难。我们最后把整个项目的目录列出来并整体总结一下：

```bash
tree -L 2
.
├── Dockerfile_local				# 前端本地的 Dockerfile
├── Dockerfile_nginx				# 前端 Nginx 的 Dockerfile
├── Dockerfile_server				# 后端 Server 的 Dockerfile
├── backend.local.env				# 后端 Server 在 docker-compose.yml 中的环境变量
├── demo_backend				# 后端项目目录
│   ├── Pipfile					# 项目依赖管理文件
│   ├── Pipfile.lock				# 同上，lock 文件
│   ├── celery					# Celery 的配置文件，可以放在任何地方
│   ├── demo_backend				# 项目配置文件和入口
│   ├── manage.py				# 本地开发入口文件
│   ├── static					# 后端 admin 和 rest 静态文件
│   ├── supervisor-master.zip			# supervisor repo，build 时下载太慢，采用本地安装
│   ├── supervisord.conf			# Supervisor 正式环境配置文件
│   ├── supervisord.local.conf			# Supervisor 开发环境配置文件
│   ├── supervisord.log				# Supervisor 运行时的 log 文件
│   ├── text_generator				# 后端的 App，本例只有一个
│   └── uwsgi.ini				# uWSGI 配置文件，用于正式环境
├── demo_frontend				# 前端项目目录
│   ├── build					# npm run build 后生成的静态文件
│   ├── config-overrides.js			# 覆盖配置 (本地 https) 使用的配置文件
│   ├── node_modules				# node modules
│   ├── package-lock.json			# package lock 文件
│   ├── package.json				# package 依赖
│   ├── public					# public 文件
│   ├── src					# 前端源代码
│   ├── ssl					# 域名 host ssl 证书相关文件
│   └── ssl.localhost				# localhost ssl 证书相关文件
├── docker-compose.yml				# docker-compose 配置文件
├── frontend.local.env				# 前端开发在 docker-compose.yml 中的环境变量
├── nginx.conf					# nginx 默认配置文件
└── nginx.proj.conf				# nginx 项目配置文件
```

> 后端的 supervisor 和 celery 文件夹以及前端的 ssl 和 ssl.localhost 理论上是可以放在其他地方的，放在这些位置只是方便开发。
>
> 很多文件或文件夹是可以 ignore 的，比如前端的 build，后端的 supervisord.log 以及模型文件等，不过为了更加方便大家查看就都推上去了。

这样我们就把前后端用 docker 完全地整合在一起，在全栈开发时可以前后端同时开发调试，正式上线时也可以快速完成部署。

另外，把映射的日志文件目录也放在这里：

```bash
cd ~/docker_volume/log
tree -L 2
.
├── celery
│   ├── err.log
│   ├── out.log
│   ├── worker1-1.log
│   ├── worker1-2.log
│   ├── worker1-3.log
│   ├── worker1-4.log
│   ├── worker1-5.log
│   ├── worker1-6.log
│   ├── worker1-7.log
│   ├── worker1-8.log
│   └── worker1.log
├── nginx
│   ├── access.log
│   ├── demo.access.log
│   ├── demo.error.log
│   └── error.log
└── uwsgi
    ├── demo.uwsgi.log
    ├── err.log
    └── out.log
```

分别是 celery、uwsgi 和 nginx 的日志文件，nginx 的 `demo.*` 就是我们针对项目做得配置，celery 的 `err.log` 和 `out.log` 是我们在 Supervisor 中做得配置，其余的则是 celery 的 conf 文件做得配置（`celeryd.conf` line 24：`CELERYD_OPTS="--time-limit=300 --concurrency=8"`）。建议把一个项目的日志放（或映射）在一个地方，无论是本地开发还是正式部署。

> 有些 log 是没必要的，比如 uwsgi，如果配置本身设置了的话，supervisor 那里可以不用设置。

## 参考文献和资源

以下主要罗列使用过的参考文献和一些还不错的资源，简单的归了下类，大家按需取用。

- [twtrubiks/docker-django-nginx-uwsgi-postgres-tutorial: Docker + Django + Nginx + uWSGI + Postgres 基本教學 - 從無到有 (Docker + Django + Nginx + uWSGI + Postgres Tutorial)](https://github.com/twtrubiks/docker-django-nginx-uwsgi-postgres-tutorial)

- Https 配置
    - [Django+uWsgi+nginx+https 完全配置 | Sunrise 博客](https://yjdwbj.github.io/2016/11/09/Django-uWsgi-nginx-https-%E5%AE%8C%E5%85%A8%E9%85%8D%E7%BD%AE/)
    - [Django + uWSGI + Nginx + SSL - request for working configuration (emphasis on SSL) - Stack Overflow](https://stackoverflow.com/questions/29827299/django-uwsgi-nginx-ssl-request-for-working-configuration-emphasis-on-ss)
    - [Nginx 配置 HTTPS 服务器 | Aotu.io「凹凸实验室」](https://aotu.io/notes/2016/08/16/nginx-https/index.html)

- SSL 证书

    - [JrCs/docker-letsencrypt-nginx-proxy-companion: LetsEncrypt companion container for nginx-proxy](https://github.com/JrCs/docker-letsencrypt-nginx-proxy-companion)
    - [How to Set Up Free SSL Certificates from Let's Encrypt using Docker and Nginx](https://www.humankode.com/ssl/how-to-set-up-free-ssl-certificates-from-lets-encrypt-using-docker-and-nginx)
    - [那些证书相关的玩意儿 (SSL,X.509,PEM,DER,CRT,CER,KEY,CSR,P12 等) - guogangj - 博客园](https://www.cnblogs.com/guogangj/p/4118605.html)
    - [细说 CA 和证书 | 小胡子哥的个人网站](https://www.barretlee.com/blog/2016/04/24/detail-about-ca-and-certs/)

- Celery
    - [How to run celery as a daemon?](https://pythad.github.io/articles/2016-12/how-to-run-celery-as-a-daemon-in-production)
    - [5. 任务状态追踪 on_message - 疯哥哥带你飞 - CSDN 博客](https://blog.csdn.net/oyw5201314ck/article/details/79669262)
    - [Asynchronous Tasks With Django and Celery – Real Python](https://realpython.com/asynchronous-tasks-with-django-and-celery/#what-is-celery)
    - [分布式队列神器 Celery - python web 学习轨迹 - SegmentFault 思否](https://segmentfault.com/a/1190000008022050)
    - [Daemonization — Celery 4.2.0 documentation](http://docs.celeryproject.org/en/latest/userguide/daemonizing.html#available-options)

- Supervisor + Nginx + uWSGI
    - [Supervisor with Docker: Lessons learned - Advanced Web Machinery](https://advancedweb.hu/2018/07/03/supervisor_docker/)
    - [Python, UWSGI, Supervisor & Nginx](https://gist.github.com/timmyomahony/1047615#file-supervisord-conf)
    - [dorianpula/ansible-nginx-uwsgi-supervisor: An Ansible role to setup and manage a UWSGI app via supervisor, and served up on a NGINX web server.](https://github.com/dorianpula/ansible-nginx-uwsgi-supervisor)
    - [Supervisor: A Process Control System — Supervisor 3.3.5 documentation](http://supervisord.org/)

    - [Setting up Django and your web server with uWSGI and nginx — uWSGI 2.0 documentation](https://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html)

    - [How to use Django with uWSGI | Django documentation | Django](https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/uwsgi/)

## 后记

这篇文章包括这个项目花了一天时间才完成，这还是在已经对各模块都有一些经验的情况下。很多地方都踩过坑，说这篇文章的内容 “坑坑洼洼” 也不夸张，尤其是我提到要注意或者特别强调的点。在解决这些坑的过程中得到不少同事的帮助，尤其是 [scottming (Scott Ming)](https://github.com/scottming) 在本地 Https 和 Dockerfile 相关的配置中给予了很多启发和提示。最后，希望这个 demo 项目和文章能对大家有所帮助，如果有 Google、Stackoverflow 没有找到答案且与此项目相关的问题或本项目疏漏的地方，欢迎大家 Issue。

## CHANGELOG

- 20190303 创建