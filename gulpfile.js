'use strict';

const gulp = require('gulp'),
      path = require('path'),
      del = require('del'),
      concat = require('gulp-concat'),
      sass = require('gulp-sass'),
      sourcemaps = require('gulp-sourcemaps');

sass.compiler = require('node-sass');

const static_dir = './pyorg/app/static/';


const lib_files = [
    'jquery/dist/jquery.js',
    'bootstrap/dist/js/bootstrap.js',
];

function libs_concat() {
    return gulp.src(lib_files.map(f => path.join('node_modules', f)))
        .pipe(concat('lib/libs.js'))
        .pipe(gulp.dest(static_dir));
}

function libs_mathjax() {
    return gulp.src('node_modules/mathjax/**/*')
        .pipe(gulp.dest(path.join(static_dir, 'lib/MathJax')));
}


const libs = gulp.parallel(libs_concat, libs_mathjax);


function compile_sass() {
    return gulp.src('./assets/**/*.scss')
        .pipe(sourcemaps.init())
        .pipe(sass({
            includePaths: ['node_modules'],
        }).on('error', sass.logError))
        .pipe(sourcemaps.write())
        .pipe(gulp.dest(static_dir));
}

function watch_sass() {
    gulp.watch('./assets/**/*.scss', ['sass']);
}


function clean() {
    return del([path.join(static_dir, '**/*')]);
}


const build = gulp.parallel(libs, compile_sass);


exports.libs = libs;
exports.sass = compile_sass;
exports.build = build;
exports.clean = clean;
exports.default = gulp.series(clean, build);
