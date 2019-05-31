let argv         = require('minimist')(process.argv.slice(2));
let autoprefixer = require('gulp-autoprefixer');
let chmod        = require('gulp-chmod');
let concat       = require('gulp-concat');
let gulp         = require('gulp');
let gulpif       = require('gulp-if');
let plumber      = require('gulp-plumber');
let pug          = require('gulp-pug');
let rename       = require('gulp-rename');
let sass         = require('gulp-sass');
let sourcemaps   = require('gulp-sourcemaps');
let uglify       = require('gulp-uglify');
let cache        = require('gulp-cached');
let spawn        = require('child_process').spawn;

let enabled = {
    uglify: argv.production,
    maps: argv.production,
    failCheck: !argv.production,
    prettyPug: !argv.production,
};


/* Order matters. First compile templates in BWA, then the local project.
 * If local templates have the same name as those in BWA, they will be used.
 * e.g. `src/templates/_footer.pug` will override the one from BWA. */
let pugs = [
    'webstatic/assets_shared/templates/**/*.pug',
    'websrc/templates/**/*.pug'
];

let sasses = [
    'webstatic/assets_shared/styles/**/*.sass',
    'websrc/styles/**/*.sass'
];


/* Stylesheets */
gulp.task('styles', function(done) {
    gulp.src('websrc/styles/**/*.sass')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(sass({
            outputStyle: 'compressed'}
            ))
        .pipe(autoprefixer("last 3 versions"))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulp.dest('webstatic/assets/css'));
    done();
});


/* Templates - Pug */
gulp.task('templates', function(done) {
    gulp.src(pugs)
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(cache('templating'))
        .pipe(pug({
            pretty: enabled.prettyPug
        }))
        .pipe(gulp.dest('templates/'));
    done();
});


/* Individual Uglified Scripts */
gulp.task('scripts', function(done) {
    gulp.src('websrc/scripts/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(cache('scripting'))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(rename({suffix: '.min'}))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(chmod(644))
        .pipe(gulp.dest('webstatic/assets/js/'));
    done();
});


/* Collection of scripts in websrc/scripts/tutti/ to merge into tutti.min.js */
/* Since it's always loaded, it's only for functions that we want site-wide */
gulp.task('scripts_tutti', function(done) {
    gulp.src('websrc/scripts/tutti/**/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(concat("tutti.min.js"))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(chmod(0o644))
        .pipe(gulp.dest('webstatic/assets/js/'));
    done();
});


// While developing, run 'gulp watch'
gulp.task('watch',function(done) {
    gulp.watch(sasses, gulp.series('styles'));
    gulp.watch(pugs, gulp.series('templates'));

    gulp.watch('websrc/scripts/*.js', gulp.series('scripts'));
    gulp.watch('websrc/scripts/tutti/*.js',gulp.series('scripts_tutti'));
    done();
});


gulp.task('shared', function(done) {
    /*
      Set the working directory of your current process as
      the directory where the target Gulpfile exists.
    */
    process.chdir('webstatic/assets_shared');

    // Run the `gulp` executable
    let child = spawn('../../node_modules/.bin/gulp');

    // Print output from Gulpfile
    child.stdout.on('data', function(data) {
        if (data) {
            console.log(data.toString());
        }
    });
    done();
});

// Run 'gulp' to build everything at once
gulp.task('default', gulp.parallel('styles', 'templates', 'scripts', 'scripts_tutti'));
