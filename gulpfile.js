'use strict';

const {src, dest, series, parallel, watch} = require('gulp');
const path = require('path'),
      del = require('del'),
      concat = require('gulp-concat'),
      sass = require('gulp-sass'),
      sourcemaps = require('gulp-sourcemaps');

sass.compiler = require('node-sass');

const static_dir = './pyorg/flask/static/',
      sass_files = './assets/**/*.scss',
      script_files = './assets/**/*.js';


const font_files = [
];

function fonts() {
    return src(font_files.map(f => path.join('node_modules', f)))
        .pipe(dest(path.join(static_dir, 'fonts')));
}


const lib_files = [
    'jquery/dist/jquery.js',
    'bootstrap/dist/js/bootstrap.js',
];

function libs_concat() {
    return src(lib_files.map(f => path.join('node_modules', f)))
        .pipe(concat('lib/libs.js'))
        .pipe(dest(static_dir));
}

function libs_mathjax() {
    return src('node_modules/mathjax/**/*')
        .pipe(dest(path.join(static_dir, 'lib/MathJax')));
}


const libs = parallel(libs_concat, libs_mathjax);



function scripts() {
    return src(script_files)
        .pipe(concat('app.js'))
        .pipe(dest(static_dir));
}


function watch_scripts() {
    watch(script_files, scripts);
}


function compile_sass() {
    return src('./assets/sass/styles.scss')
        .pipe(sourcemaps.init())
        .pipe(sass({
            includePaths: ['node_modules'],
        }).on('error', sass.logError))
        .pipe(sourcemaps.write())
        .pipe(dest(path.join(static_dir, 'styles')));
}

function watch_sass() {
    watch(sass_files, compile_sass);
}


function clean() {
    return del([path.join(static_dir, '**/*')]);
}


const build = parallel(fonts, libs, scripts, compile_sass);


exports.fonts = fonts;
exports.libs = libs;
exports.scripts = scripts;
exports.sass = compile_sass;
exports.build = build;
exports.clean = clean;
exports.watch = parallel(watch_scripts, watch_sass);
exports.default = series(clean, build);
