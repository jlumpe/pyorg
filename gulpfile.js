'use strict';

const {src, dest, series, parallel, watch} = require('gulp');
const path = require('path'),
      del = require('del'),
      concat = require('gulp-concat'),
      sass = require('gulp-sass'),
      sourcemaps = require('gulp-sourcemaps');

sass.compiler = require('node-sass');

const static_dir = './pyorg/app/static/';


const lib_files = [
    'jquery/dist/jquery.js',
    'bootstrap/dist/js/bootstrap.js',
    'popper.js/dist/popper.js',
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


function compile_sass() {
    return src('./assets/**/*.scss')
        .pipe(sourcemaps.init())
        .pipe(sass({
            includePaths: ['node_modules'],
        }).on('error', sass.logError))
        .pipe(sourcemaps.write())
        .pipe(dest(static_dir));
}

function watch_sass() {
    watch('./assets/**/*.scss', compile_sass);
}


function clean() {
    return del([path.join(static_dir, '**/*')]);
}


const build = parallel(libs, compile_sass);


exports.libs = libs;
exports.sass = compile_sass;
exports.build = build;
exports.clean = clean;
exports.watch = watch_sass;
exports.default = series(clean, build);
