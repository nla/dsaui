import os, subprocess, shlex, secrets, string, shutil, re
from tempfile import NamedTemporaryFile
from flask import Flask, render_template, request, escape, send_file

app = Flask(__name__)

raintale_home = os.environ['RAINTALE_HOME']
story_dir = os.environ.get('STORY_DIR', 'stories')


output_formats = {
    'html': 'text/html',
    'jekyll': 'text/html',

}

id_length = 10
id_alphabet = 'abcdefhjkmnpqrstuvwxyz23456789'
id_regex = re.compile('[' + id_alphabet + ']{' + str(id_length) + '}')

def generate_id():
    return ''.join(secrets.choice(id_alphabet) for i in range(id_length))


@app.route("/")
def index():
    return render_template('index.html')

@app.route('/stories/<id>')
def story_show(id):
    if not id_regex.match(id):
        return 'Story not found', 404
    return send_file(os.path.join(story_dir, id + '.html'))


@app.route('/raintale')
def raintale_form():
    storytellers = ['html', 'jekyll-html', 'jerkyll-markdown', 'markdown', 'mediawiki', 'template']
    presets = ['default', '4image-card', 'thumbnails1024', 'thumbnails3col', 'thumbnails4col',
               'vertical-bootstrapcards-imagereel']
    return render_template('raintale/form.html', storytellers=storytellers, presets=presets)


@app.route('/raintale', methods=['POST'])
def raintale_post():
    tmp_dir = os.path.join(raintale_home, 'tmp')
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    form = request.form
    id = generate_id()

    def generate():
        with NamedTemporaryFile('w', dir=tmp_dir, encoding='utf-8') as infile, \
                NamedTemporaryFile('r', dir=tmp_dir) as outfile:
            infile.write(form['urls'])
            infile.flush()
            command = ['docker-compose', 'run', 'raintale', 'tellstory',
                       '--storyteller', form['storyteller'],
                       '--preset', form['preset'],
                       '-i', 'tmp/' + os.path.basename(infile.name),
                       '-o', 'tmp/' + os.path.basename(outfile.name),
                       '--title', form['title']]
            yield '<!doctype html><pre>$ '
            yield escape(shlex.join(command) + '\n')
            process = subprocess.Popen(command, cwd=tmp_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                while True:
                    line = process.stdout.readline()
                    if line:
                        yield escape(line.decode())
                    else:
                        break
            finally:
                process.terminate()
            yield '</pre>'

            status = process.wait()
            if status != 0:
                yield '<strong>Story generation failed</strong>'
                return

            if not os.path.exists(story_dir):
                os.makedirs(story_dir)
            with open(os.path.join(story_dir, id + ".html"), 'w') as f:
                shutil.copyfileobj(outfile, f)

            yield '<script>location.href="/stories/' + id + '"</script>'

    return app.response_class(generate())


if __name__ == '__main__':
    app.run()
