from distutils.core import setup

setup(
    name='rapidsms-cvs',
    version='0.1',
    license="BSD",

    requires = [
        "rapidsms",
        'healthmodels',
        'rapidsms-xforms',
        'rapidsms-auth',
        'rapidsms-polls',
        'rapidsms-httprouter',
        'rapidsms-ureport',
    ],

    dependency_links = [
        "http://github.com/daveycrockett/healthmodels/tarball/master#egg=healthmodels",
        "http://github.com/daveycrockett/rapidsms-xforms/tarball/master#egg=rapidsms-xforms",
        "http://github.com/daveycrockett/auth/tarball/master#egg=rapidsms-auth",
        "http://github.com/daveycrockett/rapidsms-polls/tarball/master#egg=rapidsms-polls",
        "http://github.com/daveycrockett/rapidsms-httprouter/tarball/master#egg=rapidsms-httprouter",
        "http://github.com/daveycrockett/rapidsms-ureport/tarball/master#egg=rapidsms-ureport",
    ],

    description='The community vulnerability surveillance program deployed in Uganda for the VHT program',
    long_description=open('README.rst').read(),
    author='David McCann',
    author_email='david.a.mccann@gmail.com',

    url='http://github.com/daveycrockett/rapidsms-cvs',
    download_url='http://github.com/daveycrockett/rapidsms-cvs/downloads',

    include_package_data=True,

    packages=['cvs'],

    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
