
deb:
	rm -rf deb_dist
	python3 setup.py --no-user-cfg --command-packages=stdeb.command sdist_dsc --debian-version=0kosmisk --verbose --copyright-file copyright.txt -z stable
	(cd deb_dist/* && debuild -us -uc)
