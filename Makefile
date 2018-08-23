
test:
	python3 setup.py nosetests

deb:
	rm -rf deb_dist
	python3 setup.py --no-user-cfg --command-packages=stdeb.command sdist_dsc --debian-version=$${BUILD_NUMBER:-0}dbc --verbose --copyright-file copyright.txt -z stable
	(cd deb_dist/* && debuild -us -uc)

rsync:	deb
	cd deb_dist && \
	for changes in *.changes; do \
               rsync -av $(RSYNC_SSH) $$changes `sed -e '1,/^Files:/d' -e '/^[A-Z]/,$$d' -e 's/.* //' $$changes` $(RSYNC_TARGET); \
        done
