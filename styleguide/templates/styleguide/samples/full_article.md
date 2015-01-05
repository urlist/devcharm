# Must-have Django packages.

> Stop reinventing the wheel! Here is a list of packages to simplify your development.


Whether you need to integrate your web app with **StackOverflow**, run asynchronous jobs, **debug** slow pages or build an **API**, there's an extension you can easily `pip install` for it. This list contains some of the most interesting **Django** extensions out there.


## Authentication and authorization

- [Python social auth](http://psa.matiasaguirre.net/) is the most comprehensive social authentication/registration mechanism for Python. The backend support is massive: you can authenticate against **more than 50 providers**. Install it via `pip install python-social-auth`

- [Django Guardian](http://django-guardian.readthedocs.org/) implements a *per object* permissions for your models.
Install it via `pip install django-guardian`

- [Django OAuth Toolkit](http://django-oauth-toolkit.readthedocs.org/en/latest/) provides out of the box all the endpoints, data and logic needed to add **OAuth2** provider capabilities to your Django projects. It can be nicely integrated with Django REST framework.
Install it via `pip install django-oauth-toolkit`

- [django-allauth](https://github.com/pennersr/django-allauth) Integrated set of Django applications addressing authentication, registration, account management as well as 3rd party (social) account authentication.
Install it via `pip install django-allauth`

## Backend

- [Celery](http://www.celeryproject.org/). Celery is the *de facto* standard to manage asynchronous, distributed **job queues**, and it can be easily integrated in your Django app. Install it via `pip install Celery`

- [Django REST framework](http://www.django-rest-framework.org/) is an **insanely awesome** framework to build REST APIs. It manages for you serialization, throttling, content negotiation, pagination and—*drum roll*—it builds a **browsable API** for free, so developers can browse and experiment with your API from the web browser.
Install it via `pip install djangorestframework`

- [Django stored messages](http://django-stored-messages.readthedocs.org/en/latest/) is a small, non-intrusive app which integrates smoothly with Django’s messages framework (django.contrib.messages) and lets users decide which messages have to be stored on the database backend thus making them available over sessions.

- [django-cors-headers](https://github.com/ottoyiu/django-cors-headers) is a tiny app for setting up CORS headers. Very helpful to manage cross-domain requests in your Django apps (e.g. a javascript client served by a CDN). Install it via `pip install django-cors-headers`

- [South](http://south.readthedocs.org/en/latest/about.html) provides schema and data migration in a database-independent fashion. Starting from Django 1.7 South functionalities will be included in Django core but this app will be still maintained for compatibility. Intall it via `pip install South`

- [Django mailer](https://github.com/pinax/django-mailer) provides a backend for sending email (EMAIL_BACKEND) which stores emails in a queue in the database, to be sent out later from a cronjob using your actual email backend. This means you have better tolerance of your email system going down, and that sending of emails can participate in database transactions, which can be a big deal in some cases.

## Debugging

- [Debug toolbar](https://github.com/django-debug-toolbar/django-debug-toolbar). Ever wondered why your app is so freaking slow? **Debug toolbar** is a nice plugin that will show you all the `SQL` queries Django is doing to render your page, and much more. Install it via `pip install django-debug-toolbar`

- [Django pdb](https://github.com/tomchristie/django-pdb) helps you debugging views and tests. If you are in `debug mode` and you add `?pdb` on your location bar when visiting a view, **django pdb** drops you into `pdb`. Also, it integrates nicely with your test: `./manage.py test --pdb` drops into pdb on test failures. Install it via `pip install django-pdb`.


## Static Assets

- [Django Storages](http://django-storages.readthedocs.org/en/latest/) is a powerful and configurable plugin to make storing your static assets on an external service super easy. Simply run `python manage.py collectstatic` after installing it to copy all modified static files to your chosen backend. The most popular add-on works with the `python-boto` library to let you store those files on **Amazon S3** using their cheap, easy-to-use, and fast file buckets. Install it via `pip install django-storages`

- [Django Pipeline](http://django-pipeline.readthedocs.org/en/latest/) is a static asset packaging library for Django, providing both CSS and JavaScript concatenation and compression. Supporting multiple compilers (LESS, SASS, et al), multiple compressors for CSS and JS, it gives you plenty of customizability. Pipeline also [works nicely with Django Storages](http://django-pipeline.readthedocs.org/en/latest/storages.html#using-with-other-storages) and other storage backends. Install it with `pip install django-pipeline`.

- [Django Compressor](http://django-compressor.readthedocs.org/en/latest/) combines and compresses linked and inline Javascript or CSS in a Django templates into cacheable static files with optional, configurable compilers and filters for concatenation, minification, compression, precompiliation (e.g. for Sass or Coffee Script files) etc. etc. Install it with `pip install django_compressor`.

## Utils

- [Reversion](http://django-reversion.readthedocs.org/) provides version control facilities to your models. With a few configuration lines, you can recover deleted models or roll back to any point in a model's history. The integration with the Django **admin** interface takes seconds. Install it via `pip install django-reversion`

- [Django extensions](http://django-extensions.readthedocs.org/en/latest/) is a collection of **17** custom extensions for the Django Framework. The most notable ones are: `shell_plus`, a shell with autoloading of the apps database models; `RunScript`, to run scripts in the Django context; `graph_models`, to render a graphical overview of your models (it's **extremely** useful); `sqldiff`, to print the `ALTER TABLE` statements for the given appnames. Install it via `pip install django-extensions`

- [Django braces](http://django-braces.readthedocs.org/en/latest/) is a collection of reusable, generic mixins for Django providing common behaviours and patterns for views, forms and other components. Very effective on removing boilerplates.
Install it via `pip install django-braces`
