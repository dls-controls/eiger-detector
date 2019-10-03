FROM centos:7 as build

# Set the working directory to /app
WORKDIR /src

RUN yum -y update && yum -y clean all &&\
    yum groupinstall -y 'Development Tools' &&\
    yum install -y boost boost-devel cmake log4cxx-devel epel-release &&\
    yum install -y zeromq3-devel python2-pip &&\
    yum install -y libpcap-devel &&\
    yum install -y python-virtualenv &&\
    yum install -y Cython &&\
    yum -y clean all && rm -rf /var/cache/yum &&\
    cd /src &&\
    mkdir prefix &&\
    cd /src/ &&\
        curl -L -O https://www.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.1/src/hdf5-1.10.1.tar.bz2 &&\
        tar -jxf hdf5-1.10.1.tar.bz2 &&\
        mkdir -p /src/build-hdf5-1.10 && cd /src/build-hdf5-1.10 &&\
        /src/hdf5-1.10.1/configure --prefix=/usr/local && make >> /src/hdf5build.log 2>&1 && make install &&\
    cd /src/ &&\
        curl -L -s -o c-blosc-1.14.2.tar.gz -O https://github.com/Blosc/c-blosc/archive/v1.14.2.tar.gz &&\
        tar -zxf c-blosc-1.14.2.tar.gz &&\
        mkdir -p /src/build-blosc && cd /src/build-blosc &&\
        cmake /src/c-blosc-1.14.2/ && make >> /src/bloscbuild.log 2>&1 && make install &&\
    cd / && rm -rf /src/build* /src/*.tar* &&\
    cd /src &&\
    virtualenv venv &&\
    cd /src/ &&\
    git clone https://github.com/odin-detector/odin-data.git &&\
    cd /src/odin-data &&\
    git checkout tags/1.3.0 &&\
    cmake -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON -DCMAKE_INSTALL_PREFIX=/src/venv &&\
    make VERBOSE=1 && make install &&\
    cd /src/ &&\
    git clone https://github.com/odin-detector/odin-control.git &&\
    cd /src/odin-control &&\
    git checkout tags/0.9.0 &&\
    source /src/venv/bin/activate &&\
    pip install Cython &&\
    pip install numpy &&\
    pip install pkgconfig &&\
    pip install configparser &&\
    cd /src/odin-control &&\
    python setup.py install &&\
    cd /src/odin-data/tools/python &&\
    python setup.py install &&\
    cd /src &&\
    git clone https://github.com/dls-controls/eiger-detector.git &&\
    cd /src/eiger-detector &&\
    git checkout eiger-control &&\
    cd /src/eiger-detector/control &&\
    python setup.py install &&\
    cd /src/eiger-detector/data &&\
    cmake -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON -DODINDATA_ROOT_DIR=/src/venv -DCMAKE_INSTALL_PREFIX=/src/venv &&\
    make VERBOSE=1 && make install &&\
    cd /src/eiger-detector/odindeploy &&\
    echo '{' > docker_config.json &&\
    echo '  "ODIN_DATA_ROOT": "/src/venv",' >> docker_config.json &&\
    echo '  "EIGER_ROOT": "/src/venv",' >> docker_config.json &&\
    echo '  "HDF5_FILTERS": "/src/venv",' >> docker_config.json &&\
    echo '  "DETECTOR_IP": "127.0.0.1",' >> docker_config.json &&\
    echo '  "DETECTOR_CTRL_PORT": "8080"' >> docker_config.json &&\
    echo '}' >> docker_config.json


