from setuptools import setup, find_packages

setup(
    name='pmc_automation_tools',
    version='1.0.0',
    author='Dan Sleeman',
    author_email='sleemand@shapecorp.com',
    description='A collection of tools to help automate Plex Manufacturing Cloud activities.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/your-repo-name',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'pywin32>=306',
        'selenium>=4.13.0',
        'zeep~=4.2.1',
        'Requests>=2.31.0'
    ],
    entry_points={
        'console_scripts': [
        ],
    }
)
