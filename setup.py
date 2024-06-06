from setuptools import setup, find_packages

setup(
    name='Stanford SecureGPT Bot',
    version='0.1.0',
    packages=find_packages(),
    python_requires='==3.10.13',
    install_requires=[
        'selenium',
        'pandas',
        'pyperclip',
        'pytz',
        'webdriver_manager'
    ],
    entry_points={
        'console_scripts': [
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
    ],
)
