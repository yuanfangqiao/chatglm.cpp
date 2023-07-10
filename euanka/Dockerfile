FROM python:3.9-alpine 
# 使用阿里云的镜像源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

RUN apk add git gcc g++ make cmake && \
    git config --global http.proxy 'socks5://192.168.1.8:7890'  && \
    git config --global https.proxy 'socks5://192.168.1.8:7890' && \
    git config --global http.proxy http://192.168.1.8:7890  && \
    git config --global https.proxy https://192.168.1.8:7890 && \
    git clone --recursive https://github.com/yuanfangqiao/chatglm.cpp.git && \
    cd chatglm.cpp  && \
    git submodule update --init --recursive && \
    cmake -B build && cmake --build build -j

#COPY --from=build /chatglm.cpp/build/bin/main /chatglm

RUN apk add libc-dev libstdc++-dev &&  apk cache clean

RUN cd /chatglm.cpp/ && pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install websockets -i https://pypi.tuna.tsinghua.edu.cn/simple

#RUN pip install git+https://github.com/yuanfangqiao/chatglm.cpp.git@main -i https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /chatglm.cpp/euanka/

#COPY websokcet_server.py app.py

CMD ["python", "websokcet_server.py", "-m","/THUDM/chatglm2-ggml.bin"]