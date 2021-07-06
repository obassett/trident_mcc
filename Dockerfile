FROM python:3.9

ARG UID=500
ARG GID=500
ARG username=trident_mcc
ARG groupname=trident_mcc
ARG workingdir=/trident_mcc

RUN apt update -y && \
    apt upgrade -y

RUN ["pip3", "install", "poetry"]

RUN mkdir $workingdir && \
    groupadd -g $GID $groupname && \
    useradd -u $UID -g $GID --home-dir $workingdir $username && \
    chown $UID:$GID $workingdir

COPY --chown=$UID:$GID /trident-mcc $workingdir

WORKDIR $workingdir

USER $username:$groupname

RUN poetry install --no-dev --no-interaction --no-ansi

ENTRYPOINT ["/trident_mcc/trident_mcc.sh"]