gerrit_tools
============
Common tools to work with a bunch of Gerrit repositories, with help of REST API and Command Line Tools

Install
=======
Python 3.5 required
```commandline
pip install gerrit-tools
```

Setup
=====
On first run script will prompt to input several params related to your Gerrit instance.
Configuration is stored in `~/.config/gerrit_tools/config` file.
```commandline
$ gerrit_tools ...some command...
Enter value for GERRIT_URL: gerrit.yourserver.org
Enter value for GERRIT_PORT: 29418
Enter value for GERRIT_USER: admin@yourserver.org
Enter value for GERRIT_API_TOKEN: <TOKEN>
```
`<TOKEN>` is generated here: [Gerrit -> Settings -> HTTP Credentials]

Usage
=====
Example deleting `some/temp/branch` on all repositories:
```commandline
$ gerrit_tools branch delete some/temp/branch
```

Example copying `src/branch` to new `dst/branch` on all repositories:
```commandline
$ gerrit_tools branch copy src/branch dst/branch
```