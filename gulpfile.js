var argv         = require('minimist')(process.argv.slice(2));
var autoprefixer = require('gulp-autoprefixer');
var chmod        = require('gulp-chmod');
var concat       = require('gulp-concat');
var gulp         = require('gulp');
var gulpif       = require('gulp-if');
var livereload   = require('gulp-livereload');
var plumber      = require('gulp-plumber');
var pug          = require('gulp-pug');
var rename       = require('gulp-rename');
var sass         = require('gulp-sass');
var sourcemaps   = require('gulp-sourcemaps');
var uglify       = require('gulp-uglify');
var cache        = require('gulp-cached');
var spawn        = require('child_process').spawn;

var enabled = {
    uglify: argv.production,
    maps: argv.production,
    failCheck: !argv.production,
    prettyPug: !argv.production,
    liveReload: !argv.production
};


/* Order matters. First compile templates in BWA, then the local project.
 * If local templates have the same name as those in BWA, they will be used.
 * e.g. `src/templates/_footer.pug` will override the one from BWA. */
var pugs = [
    'webstatic/assets_shared/templates/**/*.pug',
    'websrc/templates/**/*.pug'
];

var sasses = [
    'webstatic/assets_shared/styles/**/*.sass',
    'websrc/styles/**/*.sass'
];


/* Stylesheets */
gulp.task('styles', function() {
    gulp.src('websrc/styles/**/*.sass')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(sass({
            outputStyle: 'compressed'}
            ))
        .pipe(autoprefixer("last 3 versions"))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulp.dest('webstatic/assets/css'))
        .pipe(gulpif(enabled.liveReload, livereload()));
});


/* Templates - Pug */
gulp.task('templates', function() {
    gulp.src(pugs)
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(cache('templating'))
        .pipe(pug({
            pretty: enabled.prettyPug
        }))
        .pipe(gulp.dest('templates/'))
        .pipe(gulpif(enabled.liveReload, livereload()));
});


/* Individual Uglified Scripts */
gulp.task('scripts', function() {
    gulp.src('websrc/scripts/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(cache('scripting'))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(rename({suffix: '.min'}))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(chmod(644))
        .pipe(gulp.dest('webstatic/assets/js/'))
        .pipe(gulpif(enabled.liveReload, livereload()));
});


/* Collection of scripts in websrc/scripts/tutti/ to merge into tutti.min.js */
/* Since it's always loaded, it's only for functions that we want site-wide */
gulp.task('scripts_tutti', function() {
    gulp.src('websrc/scripts/tutti/**/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(concat("tutti.min.js"))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(chmod(644))
        .pipe(gulp.dest('webstatic/assets/js/'))
        .pipe(gulpif(enabled.liveReload, livereload()));
});


// While developing, run 'gulp watch'
gulp.task('watch',function() {
    // Only listen for live reloads if ran with --livereload
    if (argv.livereload){
        livereload.listen();
    }

    gulp.watch(sasses,['styles']);
    gulp.watch(pugs,['templates']);

    gulp.watch('websrc/scripts/*.js',['scripts']);
    gulp.watch('websrc/scripts/tutti/*.js',['scripts_tutti']);
});


gulp.task('shared', function() {
    /*
      Set the working directory of your current process as
      the directory where the target Gulpfile exists.
    */
    process.chdir('webstatic/assets_shared');

    // Run the `gulp` executable
    var child = spawn('../../node_modules/.bin/gulp');

    // Print output from Gulpfile
    child.stdout.on('data', function(data) {
        if (data) {
            console.log(data.toString());
        }
    });
});

// Run 'gulp' to build everything at once
gulp.task('default', ['styles', 'templates', 'scripts', 'scripts_tutti']);
