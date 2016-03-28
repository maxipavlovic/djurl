import os

from hendrix.deploy.base import HendrixDeploy
from hendrix.facilities.resources import DjangoStaticResource
from txws import WebSocketFactory
from protos.protos import get_factory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_resources_for_location(disk_root, url):
    for root, dirs, files in os.walk(disk_root):
        print(url.strip('/') + '%s' % root.split(disk_root)[-1])
        yield DjangoStaticResource(
            root,
            url.strip('/') + '%s' % root.split(disk_root)[-1]
        )

if __name__ == '__main__':

    deployer = HendrixDeploy(
        options={
            'wsgi': 'djurl.wsgi.application',
            'http_port': 80,

        }
    )
    # Workaround hx dev deployment
    for res in generate_resources_for_location(BASE_DIR+'/djurl/static', '/static/'):
        deployer.resources.append(res)
    deployer.reactor.listenTCP(5600, WebSocketFactory(get_factory(deployer)))
    deployer.run()